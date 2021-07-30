from importlib import import_module

from flask import Flask, render_template, abort, Response

app = Flask(__name__)


@app.route('/node-edit/<module_name>')
def node_edit(module_name):
    try:
        module = import_module(module_name)
    except ImportError as e:
        abort(404, description=str(e))
    return render_template("node_edit_main.html", module_name=module_name)


@app.route('/node-edit/<module_name>/nodes.js')
def node_edit_js_nodes(module_name):
    try:
        module = import_module(module_name)
    except ImportError as e:
        return abort(404, description=str(e))
    js = render_template("nodes.js", module_name=module_name, module=module)
    return Response(js, mimetype="text/javascript")


if __name__ == '__main__':
    app.run()
