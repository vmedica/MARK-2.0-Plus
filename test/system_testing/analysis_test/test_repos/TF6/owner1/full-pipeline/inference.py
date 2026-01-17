"""Inference module."""
import torch
from train import SimpleNet

def load_model(path):
    """Load trained model."""
    model = SimpleNet()
    # Consumer keyword: load
    model.load_state_dict(torch.load(path))
    model.eval()
    return model

def predict(model, data):
    """Make predictions."""
    with torch.no_grad():
        output = model(data)
        predictions = torch.argmax(output, dim=1)
    return predictions

if __name__ == "__main__":
    model = load_model('model.pth')
    test_data = torch.randn(5, 10)
    results = predict(model, test_data)
    print(f"Predictions: {results}")
