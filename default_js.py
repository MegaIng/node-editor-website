from js_generator import RegisterManager, Generating
from node_types import FixedPinGenerator, SimpleDataType

registry = RegisterManager()

register = registry.register


@register(FixedPinGenerator)
def fixed_pin_gen(gen: Generating, v: FixedPinGenerator):
    out = []
    for n, pin in v.pins.items():
        if pin.in_out == "in":
            out.append(f'this.addInput({n!r}, {gen.generate(pin.type)})')
        elif pin.in_out == "out":
            out.append(f'this.addOutput({n!r}, {gen.generate(pin.type)})')
        else:
            raise ValueError(pin)
    return '\n'.join(out)


@register(SimpleDataType)
def simple_data_type_gen(gen: Generating, v: SimpleDataType):
    return repr(v.id)


register_to = registry.register_to
