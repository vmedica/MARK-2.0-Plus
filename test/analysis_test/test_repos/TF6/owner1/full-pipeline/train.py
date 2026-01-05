"""Training module."""
import torch
import torch.nn as nn
import torch.optim as optim

class SimpleNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(10, 50)
        self.fc2 = nn.Linear(50, 2)
    
    def forward(self, x):
        x = torch.relu(self.fc1(x))
        return self.fc2(x)

def train_model():
    """Train the model."""
    model = SimpleNet()
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters())
    
    # Dummy training loop
    for epoch in range(3):
        X = torch.randn(32, 10)
        y = torch.randint(0, 2, (32,))
        
        optimizer.zero_grad()
        output = model(X)
        loss = criterion(output, y)
        
        # Producer keyword: backward
        loss.backward()
        optimizer.step()
    
    # Save model
    torch.save(model.state_dict(), 'model.pth')
    print("Training complete!")

if __name__ == "__main__":
    train_model()
