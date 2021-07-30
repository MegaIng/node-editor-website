from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Literal, Generic, TypeVar, Union, TYPE_CHECKING, final

if TYPE_CHECKING:
    from typing import TypeAlias

JsonData: TypeAlias = Union[dict[str, 'JsonData'], list['JsonData'], str, float, int, bool, None]


@dataclass(frozen=True)
class DataType(ABC):
    id: str

    # Using operator overloading here has the benefit that we can implicitly use NotImplemented
    # and we get correct behaviour when we are subclassing types.

    @abstractmethod
    def __rshift__(self, other):
        """
        self >> other

        Checks if a source of type self can be connected to a target of type other
        """
        return NotImplemented

    @abstractmethod
    def __lshift__(self, other):
        """
        self << other

        Checks if a target of type self can be connected to a source of type other
        """
        return NotImplemented

    def __rrshift__(self, other):
        """
        Calls self.__lshift__
        """
        return self.__lshift__(other)

    def __rlshift__(self, other):
        """
        Calls self.__rshift__
        """
        return self.__rshift__(other)

    def can_target(self, other: DataType):
        try:
            return self >> other
        except NotImplementedError:
            return False

    def can_source(self, other: DataType):
        try:
            return self << other
        except NotImplementedError:
            return False


@dataclass(frozen=True)
class AnyDataType(DataType):
    def __rshift__(self, other):
        return True

    def __lshift__(self, other):
        return True


@dataclass(frozen=True)
class SimpleDataType(DataType):
    def __rshift__(self, other):
        if not isinstance(other, SimpleDataType):
            return NotImplemented
        return self.id == other.id

    def __lshift__(self, other):
        if not isinstance(other, SimpleDataType):
            return NotImplemented
        return self.id == other.id


@dataclass(frozen=True)
@final
class Pin:
    name: str
    in_out: Literal["in", "out"]
    type: DataType
    meta_data: dict[str, Any]


@dataclass(frozen=True)
class PinGenerator(ABC):
    @abstractmethod
    def build_pins(self, node: Node):
        pass


@dataclass(frozen=True)
class ChainPinGenerators(PinGenerator):
    generators: tuple[PinGenerator, ...]

    def build_pins(self, node: Node):
        for gen in self.generators:
            gen.build_pins(node)


@dataclass(frozen=True)
class FixedPinGenerator(PinGenerator):
    pins: dict[str, Pin]

    def build_pins(self, node: Node):
        if not set(self.pins).isdisjoint(node.pins):
            raise ValueError("Some pins already defined")
        node.pins.update(self.pins)


@dataclass(frozen=True)
class SimplePropertyPinGenerator(PinGenerator):
    property_name: str
    id_template: str
    pin_template: Pin
    copy_metadata: bool = True

    def build_pins(self, node: Node):
        count = node.values[self.property_name]
        assert isinstance(count, int)
        for i in range(count):
            p = Pin(
                self.pin_template.name.format(i),
                self.pin_template.in_out,
                self.pin_template.type,
                self.pin_template.meta_data if not self.copy_metadata else self.pin_template.meta_data.copy()
            )
            pid = self.id_template.format(i)
            assert pid not in node.pins
            node.pins[pid] = p


T = TypeVar('T')


@dataclass(frozen=True)
class Property(ABC, Generic[T]):
    default: T
    meta_data: dict[str, Any]

    @abstractmethod
    def from_json(self, json_data: JsonData) -> T:
        pass

    @abstractmethod
    def to_json(self, value: T) -> JsonData:
        pass

    @abstractmethod
    def validate(self, value: T) -> bool:
        pass


@dataclass(frozen=True)
class FloatProperty(Property[float]):
    low: float = None
    high: float = None

    def from_json(self, json_data: JsonData) -> float:
        return float(json_data)

    def to_json(self, value: T) -> JsonData:
        return value

    def validate(self, value: T) -> bool:
        assert isinstance(value, (int, float)), repr(value)
        if self.low is not None and self.low > value:
            return False
        if self.high is not None and self.high < value:
            return False
        return True


@dataclass(frozen=True)
class IntProperty(Property[float]):
    low: int = None
    high: int = None

    def from_json(self, json_data: JsonData) -> float:
        return int(json_data)

    def to_json(self, value: T) -> JsonData:
        return value

    def validate(self, value: T) -> bool:
        assert isinstance(value, (int, float)) and int(value) == value
        if self.low is not None and self.low > value:
            return False
        if self.high is not None and self.high < value:
            return False
        return True


@dataclass(frozen=True)
class ChoicesProperty(Property[str]):
    choices: tuple[str, ...]

    def from_json(self, json_data: JsonData) -> str:
        assert isinstance(json_data, str)
        return json_data

    def to_json(self, value: T) -> JsonData:
        return value

    def validate(self, value: T) -> bool:
        assert isinstance(value, str)
        return value in self.choices


@dataclass(frozen=True, eq=False)
@final
class NodeType:
    category: tuple[str, ...]
    id: str  # Valid Python/JavaScript Id
    name: str  # Pretty printed name of the type
    properties: dict[str, Property]
    pin_generator: PinGenerator
    meta_data: dict[str, Any]  # Exact usage depends on renderer.

    def create(self, node_id: str, parameter: dict[str, Any], meta_data: dict[str, Any] = None):
        if meta_data is None:
            meta_data = {}
        values = {}
        for n, p in self.properties.items():
            v = parameter.pop(n, p.default)
            if not p.validate(v):
                raise ValueError()
            values[n] = v
        node = Node(
            node_id,
            self,
            values,
            {},
            defaultdict(list),
            meta_data
        )
        self.pin_generator.build_pins(node)
        return node


@dataclass
@final
class Node:
    id: str
    type: NodeType
    values: dict[str, Any]
    pins: dict[str, Pin]
    connections: dict[str, list[tuple[str, str]]]
    meta_data: [str, Any]

    @property
    def input_pins(self) -> dict[str, Pin]:
        return {n: p for n, p in self.pins.items() if p.in_out == "in"}

    @property
    def output_pins(self) -> dict[str, Pin]:
        return {n: p for n, p in self.pins.items() if p.in_out == "out"}

    @property
    def sources(self):
        return {pid: ts for pid, ts in self.connections.items() if self.pins[pid].in_out == "in"}

    @property
    def targets(self):
        return {pid: ts for pid, ts in self.connections.items() if self.pins[pid].in_out == "out"}

    @staticmethod
    def connect(source: tuple[Node, str], dest: tuple[Node, str]):
        sp = source[0].pins[source[1]]
        dp = dest[0].pins[dest[1]]
        assert sp.in_out == "out"
        assert dp.in_out == "in"
        assert sp.type.can_target(dp.type), "Types incompatible."
        assert (dest[0].id, dest[1]) not in source[0].connections[source[1]]
        assert (source[0].id, source[1]) not in dest[0].connections[dest[1]]
        source[0].connections[source[1]].append((dest[0].id, dest[1]))
        dest[0].connections[dest[1]].append((source[0].id, source[1]))

    @staticmethod
    def disconnect(source: tuple[Node, str], dest: tuple[Node, str]):
        assert (dest[0].id, dest[1]) in source[0].connections[source[1]]
        assert (source[0].id, source[1]) in dest[0].connections[dest[1]]
        source[0].connections[source[1]].remove((dest[0].id, dest[1]))
        dest[0].connections[dest[1]].remove((source[0].id, source[1]))
