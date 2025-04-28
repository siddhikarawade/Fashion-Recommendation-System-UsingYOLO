import os
import csv
import shutil
from tqdm import tqdm
import cv2
from ultralytics import YOLO

# Paths
YOLO_MODEL_PATH = "/fashionnew/Training/yolov8m_fashion_finetuning/weights/best.pt"
PREPROCESS_INPUT = "preprocess_input"  # raw dataset
OUTPUT_BASE = "static/preprocessed"
SIAMESE_FOLDER = "static/siamese_train"
CSV_LOG = os.path.join("static", "approved_images.csv")

# Create required directories
def create_dirs():
    for category in ["upper", "lower", "full"]:
        os.makedirs(os.path.join(OUTPUT_BASE, category), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_BASE, "full", "women"), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_BASE, "full", "men"), exist_ok=True)
    os.makedirs(SIAMESE_FOLDER, exist_ok=True)

create_dirs()

# Load YOLO model
model = YOLO(YOLO_MODEL_PATH)

# Class names from your data.yaml (23 classes assumed; index 0 is '-')
class_names = ['-', 'Blouse', 'Cardigan', 'Denim-pants', 'Hoodie', 'Long-skirt',
               'Long-sleeves', 'Midi-skirts', 'Mini-skirts', 'One-piece', 'Pk-shirts',
               'Shirts', 'Short-skirt', 'Short-sleeves', 'Shorts', 'Slacks',
               'Sleeveless', 'Slim-pants', 'Straight-pants', 'Sweatpants', 'Sweatshirt',
               'T-shirts', 'Training-pants']

# Mapping for folder segregation
UPPER_CLASSES = ['Blouse', 'Cardigan', 'Hoodie', 'Long-sleeves', 'Pk-shirts', 'Shirts', 'Short-sleeves', 'Sleeveless', 'Sweatshirt', 'T-shirts']
LOWER_CLASSES = ['Denim-pants', 'Long-skirt', 'Midi-skirts', 'Mini-skirts', 'Short-skirt', 'Shorts', 'Slacks', 'Slim-pants', 'Straight-pants', 'Sweatpants', 'Training-pants']
FULL_CLASSES  = ['One-piece']

# Check if image is blurred
def is_blurred(image, threshold=100.0):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    fm = cv2.Laplacian(gray, cv2.CV_64F).var()
    return fm < threshold

# Get dominant color (simple average-based method)
def get_dominant_color(image):
    resized = cv2.resize(image, (64,64))
    avg_color = cv2.mean(resized)[:3]
    r, g, b = avg_color
    if r > 200 and g < 100: return "red"
    elif g > 200 and r < 100: return "green"
    elif b > 200: return "blue"
    elif r > 200 and g > 200: return "yellow"
    else: return "mixed"

# Process a single image; return list of processed items info.
def process_image(img_path):
    try:
        img = cv2.imread(img_path)
        if img is None or img.size == 0 or is_blurred(img):
            return []
    except Exception:
        return []
    
    results = model(img)[0]
    processed = []
    upper_detects = []
    lower_detects = []
    full_detects = []
    
    for box in results.boxes:
        cls_index = int(box.cls.item())
        if cls_index < 0 or cls_index >= len(class_names):
            continue
        detected_class = class_names[cls_index]
        if detected_class == "-":
            continue
        conf = box.conf.item()
        if conf < 0.5:
            continue
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        crop = img[y1:y2, x1:x2]
        if crop.size == 0 or is_blurred(crop):
            continue
        
        if detected_class in UPPER_CLASSES:
            upper_detects.append((detected_class, crop))
        if detected_class in LOWER_CLASSES:
            lower_detects.append((detected_class, crop))
        if detected_class in FULL_CLASSES:
            full_detects.append((detected_class, crop))
    
    # For upper and lower: save image with filename = <class>.jpg (overwrite if exists)
    for det in upper_detects:
        class_label, crop = det
        color = get_dominant_color(crop)
        dest_dir = os.path.join(OUTPUT_BASE, "upper")
        os.makedirs(dest_dir, exist_ok=True)
        new_filename = f"{class_label}.jpg"   # single file per detection type
        save_path = os.path.join(dest_dir, new_filename)
        cv2.imwrite(save_path, crop)
        processed.append((new_filename, "upper", class_label, color, "unisex", save_path))
        
    for det in lower_detects:
        class_label, crop = det
        color = get_dominant_color(crop)
        dest_dir = os.path.join(OUTPUT_BASE, "lower")
        os.makedirs(dest_dir, exist_ok=True)
        new_filename = f"{class_label}.jpg"
        save_path = os.path.join(dest_dir, new_filename)
        cv2.imwrite(save_path, crop)
        processed.append((new_filename, "lower", class_label, color, "unisex", save_path))
        
    # For full: save with numeric indices.
    for det in full_detects:
        class_label, crop = det
        color = get_dominant_color(crop)
        gender = "women"  # Assume One-piece is for women; modify if needed.
        dest_dir = os.path.join(OUTPUT_BASE, "full", gender)
        os.makedirs(dest_dir, exist_ok=True)
        count = len([fname for fname in os.listdir(dest_dir) if fname.lower().endswith(".jpg")]) + 1
        new_filename = f"{class_label.replace('-', '_').lower()}{count}.jpg"
        save_path = os.path.join(dest_dir, new_filename)
        cv2.imwrite(save_path, crop)
        processed.append((new_filename, "full", class_label, color, gender, save_path))
    
    # If image has both an upper and a lower detection, copy it to siamese folder.
    if upper_detects and lower_detects:
        siamese_dir = SIAMESE_FOLDER
        os.makedirs(siamese_dir, exist_ok=True)
        count = len(os.listdir(siamese_dir)) + 1
        siamese_filename = f"siamese_{count}.jpg"
        siamese_path = os.path.join(siamese_dir, siamese_filename)
        shutil.copy(img_path, siamese_path)
        processed.append((siamese_filename, "siamese", "upper_lower", "N/A", "unisex", siamese_path))
    
    return processed

def batch_preprocess(input_folder, output_folder):
    all_images = []
    for root, _, files in os.walk(input_folder):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in ['.jpg', '.jpeg', '.png']:
                all_images.append(os.path.join(root, file))
    
    batch_size = 200
    total_batches = (len(all_images) + batch_size - 1) // batch_size
    approved_count = 0
    
    with open(CSV_LOG, mode='w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["filename", "category", "class", "color", "gender", "path", "status"])
        for i in range(total_batches):
            print(f"Processing batch {i+1}/{total_batches}...")
            batch = all_images[i*batch_size:(i+1)*batch_size]
            for img_path in tqdm(batch):
                processed = process_image(img_path)
                for entry in processed:
                    writer.writerow(list(entry) + ["approved"])
                    approved_count += 1
            if i < total_batches - 1:
                cont = input(f"Completed batch {i+1}/{total_batches}. Continue? (y/n): ").strip().lower()
                if cont != 'y':
                    break
    return f"Preprocessing completed. Total approved images: {approved_count}."

if __name__ == "__main__":
    msg = batch_preprocess(PREPROCESS_INPUT, OUTPUT_BASE)
    print(msg)

