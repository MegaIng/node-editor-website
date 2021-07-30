import sys
import traceback
from cmd import Cmd
from shlex import split
from typing import Callable, Literal, Iterable

from node_types import Node, Pin, NodeType, Property, FloatProperty, ChoicesProperty


def print_table(entries: list[tuple[str, ...]], header: tuple[str, ...] = None, sep='', pad=' ', file=sys.stdout):
    if header is not None:
        entries = [header] + entries
    if not entries:
        return
    max_widths = [0] * len(entries[0])
    for e in entries:
        if len(e) != len(max_widths):
            raise ValueError(f"Malformed table entry {e=}, {max_widths=}")
        for i, v in enumerate(e):
            max_widths[i] = max(max_widths[i], len(v))
    for e in entries:
        print(*(
            f'{pad}{v:{w}}{pad}'
            for v, w in zip(e, max_widths)
        ), sep=sep, file=file)


def _format_pin(node: Node, pid: str):
    return str([f"{n}.{p}" for n, p in node.connections.get(pid, ())])


def format_pins(node: Node, pins: Iterable[str]):
    return '{' + ', '.join(f"{pid}: {_format_pin(node, pid)}" for pid in pins) + '}'


class NodeCmd(Cmd):
    node_types: dict[str, NodeType]
    nodes: dict[str, Node]

    prompt = "> "

    def __init__(self, node_types: list[NodeType], **kwargs):
        super(NodeCmd, self).__init__(**kwargs)
        self.node_types = {t.id: t for t in sorted(node_types, key=lambda t: (t.category, t.id))}
        self.nodes = {}

    def onecmd(self, line: str) -> bool:
        try:
            return super(NodeCmd, self).onecmd(line)
        except Exception:
            traceback.print_exc(file=self.stdout)

    def print_types(self, filter_func: Callable[[NodeType], bool] = lambda _: bool):
        print_table([
            ('/'.join(t.category), t.id, t.name, str(list(t.properties.keys())))
            for t in self.node_types.values()
            if filter_func(t)
        ], header=("Category", "Type id", "Type name", "Properties"))

    def print_nodes(self, filter_func: Callable[[Node], bool] = lambda *_: bool):
        print_table([
            (i, n.type.name, f"{format_pins(n, n.input_pins)} -> {format_pins(n, n.output_pins)}")
            for i, n in self.nodes.items()
            if filter_func(n)
        ], header=("Node id", "Type name", "Inputs -> Outputs"))

    def parseparameter(self, param: Property, value: str):
        try:
            func = getattr(self, "parse_" + type(param).__name__)
        except AttributeError:
            return value
        return func(param, value)

    def completeparameter(self, param: Property, prefix: str):
        try:
            func = getattr(self, "completeparam_" + type(param).__name__)
        except AttributeError:
            return []
        return func(param, prefix)

    def emptyline(self) -> bool:
        pass

    def parse_FloatProperty(self, param: FloatProperty, value: str):
        return float(value)

    def completeparam_ChoicesProperty(self, param: ChoicesProperty, prefix: str):
        return [str(c) for c in param.choices if str(c).startswith(prefix)]

    def do_EOF(self, arg):
        return True

    def do_types(self, arg):
        """ types
        Lists the available node types
        """
        self.print_types()

    def do_nodes(self, arg):
        """ nodes
        Lists the defined nodes
        """
        self.print_nodes()

    def do_create(self, arg):
        """ create <id> <type> <arguments...>
        Creates a node
        """
        new_id, types, *args = split(arg)
        if new_id in self.node_types:
            raise ValueError(f"{new_id} already defined")
        nt = self.node_types[types]
        if len(args) > len(nt.properties):
            raise ValueError(f"To many arguments (expected at most {len(nt.properties)})")
        self.nodes[new_id] = nt.create(new_id, {
            n: self.parseparameter(p, v)
            for (n, p), v in zip(nt.properties.items(), args)
        })

    def complete_create(self, text, line, begidx, endidx):
        args = split(line[:begidx])
        if len(args) == 2:
            return [n for n in self.node_types if n.startswith(text)]
        elif len(args) >= 2:
            try:
                nt = self.node_types[args[2]]
                param = nt.properties[list(nt.properties)[len(args) - 3]]
            except (KeyError, IndexError):
                return []
            else:
                comp = self.completeparameter(param, text)
                return comp
        else:
            return []

    def do_connect(self, arg):
        source, target = split(arg)
        src_node, src_pin = source.split(".")
        tar_node, tar_pin = target.split(".")
        src_node = self.nodes[src_node]
        tar_node = self.nodes[tar_node]
        Node.connect((src_node, src_pin), (tar_node, tar_pin))

    def _complete_pin(self, prefix: str, mode: Literal["in", "out"]):
        if "." in prefix:
            src_node_name, pin_prefix = prefix.split(".")
            src_node = self.nodes[src_node_name]
            return [f"{src_node_name}.{pin_name}"
                    for pin_name, pin in src_node.pins
                    if pin_name.startswith(pin_prefix) and mode in pin.io]
        else:
            return [n for n in self.nodes if n.startswith(prefix)]

    def complete_connect(self, text, line, begidx, endidx):
        try:
            args = split(line[:begidx])
            if len(args) == 1:
                return self._complete_pin(text, "out")
            elif len(args) == 2:
                return self._complete_pin(text, "in")
            else:
                return []
        except Exception as e:
            return []
