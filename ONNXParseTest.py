import onnx

# Load the ONNX model
model = onnx.load("simple_nn.onnx")
onnx.checker.check_model(model)

# Print basic model info
print("Model Graph:")
print(model.graph)

# Iterate and print details of each node
for node in model.graph.node:
    print(f"Node Name: {node.name}")
    print(f"Inputs: {node.input}")
    print(f"Outputs: {node.output}")
    print("-----")
