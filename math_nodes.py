import operator
from abc import abstractmethod, ABC
from dataclasses import dataclass, field
from typing import Optional, Callable, Any

from node_types import *
from graphlib import TopologicalSorter

ConstantNodeType = NodeType(
    ('math',),
    "constant",
    "Constant",
    {
        "value": FloatProperty(1.0, {})
    },
    FixedPinGenerator({
        "out": Pin("Output", "out", SimpleDataType("number"), {})
    }),
    {}
)

PrinterNodeType = NodeType(
    ('math',),
    "printer",
    "Printer",
    {},
    FixedPinGenerator({
        "in": Pin("Input", "in", SimpleDataType("number"), {})
    }),
    {}
)

BinopNodeType = NodeType(
    ('math',),
    "binop",
    "Binary Operation",
    {
        "operator_name": ChoicesProperty("add", {}, ("add", "sub", "mul", "truediv"))
    },
    FixedPinGenerator({
        "a": Pin("A", "in", SimpleDataType("number"), {}),
        "b": Pin("B", "in", SimpleDataType("number"), {}),
        "res": Pin("Result", "out", SimpleDataType("number"), {}),
    }),
    {}
)

node_types = [ConstantNodeType, PrinterNodeType, BinopNodeType]


class MathCalculator:
    def calc(self, node: Node, ins: list[float]) -> list[float]:
        f = getattr(self, "calc_" + node.type.id)
        return f(node, ins)

    def calc_constant(self, node: Node, ins: list[float]) -> list[float]:
        return [node.values["value"]]

    def calc_printer(self, node: Node, ins: list[float]) -> list[float]:
        print(*ins)
        return []

    def calc_binop(self, node: Node, ins: list[float]) -> list[float]:
        op = getattr(operator, node.values["operator_name"])
        return [op(*ins)]

    def evaluate(self, nodes: dict[str, Node]):
        sorter = TopologicalSorter()
        for name, node in nodes.items():
            sorter.add(name, *(tn for pn, p in node.input_pins.items() for tn, tp in node.connections[pn]))
        sorter.prepare()
        values = {}
        while sorter.is_active():
            for name in sorter.get_ready():
                node = nodes[name]
                ins = [values[t] for pn, p in node.input_pins.items() for t in node.connections[pn]]
                outs = self.calc(node, ins)
                for p, v in zip(node.output_pins, outs):
                    values[(name, p)] = v
                sorter.done(name)


if __name__ == '__main__':
    from node_cmd import NodeCmd


    class MathCmd(NodeCmd):
        def do_evaluate(self, arg):
            calc = MathCalculator()
            calc.evaluate({s: n for s, n in self.nodes.items()})


    DEFAULT = """
        create v1 constant 5
        create v2 constant 7
        create a1 binop add
        create s1 binop sub
        create p1 printer
        
        connect v1.out a1.a
        connect v2.out a1.b
        connect v1.out s1.a
        connect v2.out s1.b
        
        connect a1.res p1.in 
        connect s1.res p1.in 
    """

    nc = MathCmd(node_types)
    nc.cmdqueue.extend(filter(None, map(str.strip, DEFAULT.splitlines())))
    nc.cmdloop()
