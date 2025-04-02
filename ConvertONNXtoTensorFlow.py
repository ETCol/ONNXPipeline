import onnx
import onnx_tf
from onnx_tf.backend import prepare

onnx_model = onnx.load("simple_nn.onnx")
tf_rep = prepare(onnx_model)
tf_rep.export_graph("model.pb")