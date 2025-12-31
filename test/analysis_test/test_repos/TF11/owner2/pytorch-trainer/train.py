"""PyTorch training script."""
import torch
import torch.nn as nn

class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc = nn.Linear(10, 2)
    
    def forward(self, x):
        return self.fc(x)

model = Net()
optimizer = torch.optim.SGD(model.parameters(), lr=0.01)
criterion = nn.CrossEntropyLoss()

# Training loop
for epoch in range(5):
    X = torch.randn(16, 10)
    y = torch.randint(0, 2, (16,))
    
    optimizer.zero_grad()
    output = model(X)
    loss = criterion(output, y)
    
    # Producer keyword: backward
    loss.backward()
    optimizer.step()

print("Training complete!")
