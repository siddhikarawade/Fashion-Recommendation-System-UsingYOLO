import os
import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import models, transforms
from torch.utils.data import Dataset, DataLoader
from PIL import Image

class SiameseDataset(Dataset):
    def __init__(self, image_folder, transform=None):
        self.image_folder = image_folder
        self.transform = transform
        self.images = []
        for file in os.listdir(image_folder):
            if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                self.images.append(os.path.join(image_folder, file))
    
    def __len__(self):
        return len(self.images)
    
    def __getitem__(self, idx):
        img_path = self.images[idx]
        image = Image.open(img_path).convert('RGB')
        if self.transform:
            image = self.transform(image)
        return image, image, torch.tensor(1.0)

class SiameseNetwork(nn.Module):
    def __init__(self):
        super(SiameseNetwork, self).__init__()
        self.cnn = models.resnet18(pretrained=True)
        self.cnn.fc = nn.Identity()
    
    def forward_once(self, x):
        return self.cnn(x)
    
    def forward(self, img1, img2):
        out1 = self.forward_once(img1)
        out2 = self.forward_once(img2)
        return out1, out2

class ContrastiveLoss(nn.Module):
    def __init__(self, margin=1.0):
        super(ContrastiveLoss, self).__init__()
        self.margin = margin
    
    def forward(self, output1, output2, label):
        dist = nn.functional.pairwise_distance(output1, output2)
        loss = torch.mean(label * dist**2 + (1 - label) * torch.clamp(self.margin - dist, min=0.0)**2)
        return loss

transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor()
])

dataset = SiameseDataset("static/siamese_train", transform=transform)
dataloader = DataLoader(dataset, batch_size=16, shuffle=True)

model = SiameseNetwork().to("cuda" if torch.cuda.is_available() else "cpu")
criterion = ContrastiveLoss(margin=1.0)
optimizer = optim.Adam(model.parameters(), lr=1e-4)

num_epochs = 5
for epoch in range(num_epochs):
    running_loss = 0.0
    for img1, img2, label in dataloader:
        img1, img2, label = img1.to("cuda" if torch.cuda.is_available() else "cpu"), img2.to("cuda" if torch.cuda.is_available() else "cpu"), label.to("cuda" if torch.cuda.is_available() else "cpu")
        optimizer.zero_grad()
        output1, output2 = model(img1, img2)
        loss = criterion(output1, output2, label)
        loss.backward()
        optimizer.step()
        running_loss += loss.item()
    print(f"Epoch {epoch+1}/{num_epochs}, Loss: {running_loss/len(dataloader):.4f}")

print("Siamese network training complete!")
torch.save(model.state_dict(), "siamese_model.pth")

