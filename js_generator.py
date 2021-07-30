from __future__ import annotations

from dataclasses import dataclass, field
from textwrap import dedent
from typing import Generic, TypeVar, Type, Callable, Union, Any, Optional

from node_types import NodeType

T = TypeVar('T')


@dataclass
class JSGenerator:
    static: dict[type, str] = field(default_factory=dict)
    dynamic: dict[type, Callable[[Generating, Any], str]] = field(default_factory=dict)

    def register(self, t: type[T],
                 static: Optional[str],
                 dynamic: Union[str, Callable[[JSGenerator, T], str]]):
        if t in self.static:
            raise ValueError(t)
        self.static[t] = static
        if not callable(dynamic):
            self.dynamic[t] = lambda *_: dynamic
        else:
            self.dynamic[t] = dynamic


class Generating:
    def __init__(self, generator: JSGenerator):
        self.generator = generator
        self.code_blocks = {}

    def generate(self, obj) -> str:
        t = type(obj)
        s = self.generator.static[t]
        d = self.generator.dynamic[t](self, obj)
        self.code_blocks[t] = s
        return d

    def node_type(self, node_type: NodeType):
        if node_type in self.code_blocks:
            return
        pin_generation = self.generate(node_type.pin_generator)
        properties = ";\n            ".join(
            self.generate(prop).format(name=name) for name, prop in node_type.properties.items()
        )
        code = dedent(f"""
        function {node_type.id}()
        {{
            {properties}
            this.pin_generation = function () {{
                {pin_generation}
            }};
            this.pin_generation();
        }}
        {node_type.id}.title = {node_type.name!r};
        LiteGraph.registerNodeType({'/'.join((*node_type.category, node_type.id))!r}, {node_type.id})
        """)
        self.code_blocks[node_type] = code

    def build(self) -> str:
        return '\n\n'.join(filter(None, self.code_blocks.values()))



@dataclass
class RegisterManager:
    static: dict[type, str] = field(default_factory=dict)
    dynamic: dict[type, Union[Callable[..., str]]] = field(default_factory=dict)
    _registered_to: list[JSGenerator] = field(default_factory=list)

    def register(self, t, static=None, dynamic=None):
        assert t not in self.static
        self.static[t] = static

        def set_dynamic(f):
            self.dynamic[t] = f
            return f

        if dynamic is None:
            return set_dynamic
        else:
            set_dynamic(dynamic)

    def register_to(self, gen: JSGenerator):
        if gen in self._registered_to:
            return
        self._registered_to.append(gen)
        for t in (set(self.static) | set(self.dynamic)):
            gen.register(t, self.static.get(t, None), self.dynamic.get(t, ''))
