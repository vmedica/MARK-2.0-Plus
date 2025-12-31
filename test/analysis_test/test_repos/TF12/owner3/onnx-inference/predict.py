"""ONNX Runtime inference."""
import onnxruntime as ort
import numpy as np

# Consumer keyword: InferenceSession
session = ort.InferenceSession('model.onnx')

input_name = session.get_inputs()[0].name
test_data = np.random.random((1, 10)).astype(np.float32)

# Consumer keyword: run
results = session.run(None, {input_name: test_data})

print(f"Predictions: {results[0]}")
