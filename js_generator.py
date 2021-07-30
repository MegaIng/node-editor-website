from __future__ import annotations

from dataclasses import dataclass, field
from textwrap import dedent
from typing import Generic, TypeVar, Type, Callable, ParamSpec, Union, Any, Optional

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
            f""
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
        {node_type.id}.title = {node_type.name};
        LiterGraph.registerNodeType("{'/'.join((*node_type.category, node_type.id))}", {node_type.id})
        """)
        self.code_blocks[node_type] = code

    def build(self) -> str:
        pass
