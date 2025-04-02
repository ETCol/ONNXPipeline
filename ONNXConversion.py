import torch
import torch.nn as nn
import torch.optim as optim
import onnx
import onnxruntime

# Assuming we have dataset and dataloader set up
# For demonstration purposes, let's create some random inputs and labels
inputs = torch.randn(32, 784)  # Assuming batch size of 32 and input size of 784
labels = torch.randint(0, 10, (32,))  # Assuming 10 classes and batch size of 32


# Definition of a simple neural network model
class SimpleNN(nn.Module):
    def __init__(self):
        super(SimpleNN, self).__init__()
        self.fc1 = nn.Linear(784, 128)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(128, 10)

    def forward(self, x):
        x = torch.flatten(x, 1)
        x = self.fc1(x)
        x = self.relu(x)
        x = self.fc2(x)
        return x


# Instantiate the model
model = SimpleNN()

# Define loss function and optimizer
criterion = nn.CrossEntropyLoss()
optimizer = optim.SGD(model.parameters(), lr=0.01)

# Define the number of epochs
num_epochs = 10

# Train the model
for epoch in range(num_epochs):
    # Forward pass
    outputs = model(inputs)
    loss = criterion(outputs, labels)

    # Backward pass and optimization
    optimizer.zero_grad()
    loss.backward()
    optimizer.step()


test_input = torch.randn(1, 784)  # A dummy input to trace the model
torch.onnx.export(model, test_input, "simple_nn.onnx", verbose=True)