import os
from PIL import Image
import torch
import torchvision.transforms as transforms
from torchvision import models
from sklearn.metrics.pairwise import cosine_similarity
from concurrent.futures import ThreadPoolExecutor

device = "cuda" if torch.cuda.is_available() else "cpu"

model = models.resnet18(pretrained=True)
model.fc = torch.nn.Identity()
model.eval().to(device)

transform = transforms.Compose([
    transforms.Resize((224,224)),
    transforms.ToTensor()
])

def extract_feature(img_path):
    img = Image.open(img_path).convert("RGB")
    img_tensor = transform(img).unsqueeze(0).to(device)
    with torch.no_grad():
        feat = model(img_tensor)
    return feat.cpu().numpy()

def find_best_matches(input_image, category_folder, top_n=6):
    input_feat = extract_feature(input_image)
    scores = []
    
    def process_file(file):
        path = os.path.join(category_folder, file)
        feat = extract_feature(path)
        sim = cosine_similarity(input_feat, feat)[0][0]
        return sim, path
    
    files = [f for f in os.listdir(category_folder) if f.lower().endswith(('.jpg','.jpeg','.png'))]
    with ThreadPoolExecutor() as executor:
        results = executor.map(process_file, files)
        for sim, path in results:
            scores.append((sim, path))
    scores.sort(key=lambda x: x[0], reverse=True)
    return [path for _, path in scores[:top_n]]

def recommend_from_image(input_image):
    # Simple heuristic: if input filename contains 'upper', recommend from lower folder; else vice-versa.
    if "upper" in input_image.lower():
        rec_category = os.path.join("static", "preprocessed", "lower")
    elif "lower" in input_image.lower():
        rec_category = os.path.join("static", "preprocessed", "upper")
    else:
        rec_category = os.path.join("static", "preprocessed", "upper")
    
    recs = find_best_matches(input_image, rec_category, top_n=6)
    relative_paths = []
    for path in recs:
        idx = path.find("static")
        if idx != -1:
            relative_paths.append(path[idx:])
        else:
            relative_paths.append(path)
    return relative_paths

