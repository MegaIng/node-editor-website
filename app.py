from importlib import import_module

from flask import Flask, render_template, abort, Response

from js_generator import Generating, JSGenerator
import default_js

app = Flask(__name__)

js_generator = JSGenerator()
default_js.register_to(js_generator)


@app.route('/node-edit/<module_name>')
def node_edit(module_name):
    try:
        module = import_module(module_name)
    except ImportError as e:
        return abort(404, description=str(e))
    try:
        module.node_types
    except AttributeError as e:
        return abort(404, description=str(e))
    try:
        js_module = import_module(module.js_module_name)
    except AttributeError:
        pass
    except ImportError as e:
        return abort(404, description=str(e))
    return render_template("node_edit_main.html", module_name=module_name)


@app.route('/node-edit/<module_name>/nodes.js')
def node_edit_js_nodes(module_name):
    try:
        module = import_module(module_name)
    except ImportError as e:
        return abort(404, description=str(e))
    try:
        js_module = import_module(module.js_module_name)
    except AttributeError:
        pass
    except ImportError as e:
        return abort(404, description=str(e))
    else:
        js_module.register_to(js_generator)
    nts = module.node_types
    gen = Generating(js_generator)
    for nt in nts:
        gen.node_type(nt)
    return Response(gen.build(), mimetype="text/javascript")


if __name__ == '__main__':
    app.run()
