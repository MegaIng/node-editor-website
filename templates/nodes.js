
{% for node_type in module.node_types() %}

function {{ node_type.id }}()
{
    {% for input in node_type.inputs%}
    this.addInput("A", "number");
    this.addInput("B", "number");
    this.addOutput("A+B", "number");
}

MyAddNode.title = {{node_type.name}};

MyAddNode.prototype.onExecute = function ()
{
    var A = this.getInputData(0);
    if (A === undefined)
        A = 0;
    var B = this.getInputData(1);
    if (B === undefined)
        B = 0;
    this.setOutputData(0, A + B)
}
</script>

LiteGraph.registerNodeType("custom/my_add", MyAddNode)

{% endfor %}