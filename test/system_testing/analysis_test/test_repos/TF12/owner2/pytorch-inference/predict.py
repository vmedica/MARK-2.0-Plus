"""PyTorch inference script."""
import torch

# Consumer keyword: load
model = torch.load('model.pth')
model.eval()

test_data = torch.randn(5, 10)

with torch.no_grad():
    predictions = model(test_data)

print(f"Predictions: {predictions}")
