from flask import Flask, render_template, request, redirect, url_for,session, flash,jsonify
from flask_mysqldb import MySQL
import MySQLdb.cursors
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
import os
import cv2
import torch
import random 
import random
from ultralytics import YOLO
# import base64
from PIL import Image
from io import BytesIO
from preprocess import batch_preprocess
from recommendation_engine import recommend_from_image
import time

UPLOAD_FOLDER = 'static/uploads'
PREPROCESS_INPUT = 'preprocess_input'
PREPROCESS_OUTPUT = 'static/preprocessed'

app = Flask(__name__)
app.secret_key = "supersecretkey"

# Database Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'  
app.config['MYSQL_PASSWORD'] = ''  # Add your MySQL password if there
app.config['MYSQL_DB'] = 'fashion_db'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)
bcrypt = Bcrypt(app)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Define folder paths (adjust as needed)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static", "images")
OUTPUT_DIR = os.path.join(STATIC_DIR, "output")
RECOMMEND_DIR = os.path.join(STATIC_DIR, "recommendations")
UPLOAD_DIR = os.path.join(STATIC_DIR, "uploads")

# Create necessary directories if they don't exist
for folder in [OUTPUT_DIR, RECOMMEND_DIR, UPLOAD_DIR]:
    os.makedirs(folder, exist_ok=True)
for sub in ['upper', 'lower', 'full']:
    os.makedirs(os.path.join(OUTPUT_DIR, sub), exist_ok=True)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Load YOLOv8 model (update path as needed)
yolo_model = YOLO("C:/Users/siddhi karawade/Desktop/fashionnew/Training/yolov8m_fashion_finetuning/weights/best.pt")
# Load feature extractor (e.g. ResNet50-based)
# feature_extractor = load_feature_extractor()

# Mapping from class names to categories (update as needed)
CLASS_CATEGORY_MAPPING = {
    'Blouse': 'upper',
    'Cardigan': 'upper',
    'Hoodie': 'upper',
    'Long-sleeves': 'upper',
    'Pk-shirts': 'upper',
    'Shirts': 'upper',
    'Short-sleeves': 'upper',
    'Sleeveless': 'upper',
    'T-shirts': 'upper',

    'Denim-pants': 'lower',
    'Long-skirt': 'lower',
    'Midi-skirts': 'lower',
    'Short-skirt': 'lower',
    'Shorts': 'lower',
    'Slacks': 'lower',
    'Slim-pants': 'lower',
    'Straight-pants': 'lower',
    'Sweatpants': 'lower',
    'Training-pants': 'lower',

    'One-piece': 'full'
}

# Global variable to store the last processed image path
current_image_path = None


# ------------------ Render HTML Pages ------------------

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register')
def register_page():
    return render_template('register.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/option')
def option_page():
    return render_template('option.html')

# admin control

# @app.route('/admin', methods=['GET'])
# def admin():
#     return render_template('admin.html')

# @app.route('/admin/preprocess', methods=['POST'])
# def start_preprocessing():
#     msg = batch_preprocess(PREPROCESS_INPUT, PREPROCESS_OUTPUT)
#     flash(msg)
#     return redirect(url_for('admin'))

@app.route('/results', methods=['GET', 'POST'])
def upload_image():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash("No file part")
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            flash("No file selected")
            return redirect(request.url)

        if file:
            filename = secure_filename(file.filename)

            # Save to a fixed path for captured image or dynamic for uploaded
            if filename == 'captured.jpg':
                filename = 'captured.jpg'  # Always overwrite the same file
            else:
                # filename = f"user_{int(time.time())}_{filename}"  # Optional unique name
                filename = secure_filename(file.filename)

            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            session['last_image'] = filename
            return redirect(url_for('upload_image'))

    # GET request (e.g. refresh)
    filename = session.get('last_image')
    if not filename:
        flash("No image found for recommendation.")
        return redirect(url_for('option_page'))

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    # ✅ Validation: OpenCV checks for blank or dark images
    try:
        import cv2
        import numpy as np

        img = cv2.imread(filepath)

        if img is None:
            flash("Could not read the image. Try again.")
            return redirect(url_for('option_page'))

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        variance = np.var(gray)
        brightness = np.mean(gray)

        # ✅ Thresholds can be tuned
        if variance < 15 or brightness < 20:
            flash("Image too dark or blank. Please capture or upload a clearer outfit image.")
            return redirect(url_for('option_page'))
    except Exception as e:
        print("OpenCV check failed:", str(e))
        flash("Failed to analyze image.")
        return redirect(url_for('option_page'))

    try:
        # YOLO prediction
        results = yolo_model(filepath)
        detected_classes = []
        for box in results[0].boxes:
            class_id = int(box.cls[0])
            if class_id in results[0].names:
                detected_classes.append(results[0].names[class_id])

        # ✅ Extra check: No clothing detected
        if not detected_classes:
            flash("No clothing detected in the image. Please try a clearer image.")
            return redirect(url_for('option_page'))

        is_upper = any(cls in CLASS_CATEGORY_MAPPING and CLASS_CATEGORY_MAPPING[cls] == 'upper' for cls in detected_classes)
        target_category = 'lower' if is_upper else 'upper'

        # Prepare recommendation directory
        target_path = os.path.join("static", "preprocessed", target_category)
        items_by_category = {}

        for root, _, files in os.walk(target_path):
            for f in files:
                if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                    base_category = f.split('_')[0].lower()
                    items_by_category.setdefault(base_category, []).append(os.path.join(root, f))

        available_categories = list(items_by_category.keys())
        if not available_categories:
            flash("No recommendations available.")
            return redirect(url_for('option_page'))

        selected_categories = random.sample(available_categories, min(6, len(available_categories)))
        recommendations = [random.choice(items_by_category[cat]).replace('\\', '/') for cat in selected_categories]

        print(f"Selected {len(recommendations)} items from unique categories: {selected_categories}")

        return render_template('results.html',
                               input_img=filename,
                               recommendations=recommendations)

    except Exception as e:
        print(f"Error processing image: {str(e)}")
        flash("Error processing image. Please try again.")
        return redirect(url_for('option_page'))



# @app.route('/capture', methods=['POST'])
# def capture():
#     try:
#         data = request.get_json()
#         print("Received data:", data)

#         if not data or "image" not in data:
#             return jsonify({"message": "No image data received"}), 400

#         image_data = data["image"]
#         if "," not in image_data:
#             return jsonify({"message": "Invalid image format"}), 400

#         header, encoded = image_data.split(",", 1)
#         image_bytes = base64.b64decode(encoded)

#         try:
#             image = Image.open(BytesIO(image_bytes))
#         except Exception as e:
#             print("PIL error:", e)
#             return jsonify({"message": "Could not decode image"}), 400

#         global current_image_path
#         current_image_path = os.path.join(UPLOAD_DIR, "captured.jpg")
#         image.save(current_image_path)

#         print("✅ Image saved at:", current_image_path)
#         return jsonify({ "redirect": url_for("process") })

#     except Exception as e:
#         print("❌ Unexpected capture error:", e)
#         return jsonify({"message": "Failed to process image"}), 500


# def get_recommendations(image_path):
#     """Helper function to get recommendations based on image detection with fresh randomization"""
#     # Seed random with current timestamp for unique selections
#     random.seed(time.time())
    
#     results = yolo_model(image_path)
#     detected_classes = []
    
#     # Get detected classes
#     for box in results[0].boxes:
#         class_id = int(box.cls[0])
#         class_name = results[0].names[class_id]
#         detected_classes.append(class_name)
    
#     print("Detected classes:", detected_classes)  # Debug print
    
#     # Determine category
#     is_upper = any(cls in CLASS_CATEGORY_MAPPING and CLASS_CATEGORY_MAPPING[cls] == 'upper' for cls in detected_classes)
#     is_lower = any(cls in CLASS_CATEGORY_MAPPING and CLASS_CATEGORY_MAPPING[cls] == 'lower' for cls in detected_classes)
    
#     # Set opposite category for recommendations
#     if is_upper:
#         target_category = 'lower'
#     elif is_lower:
#         target_category = 'upper'
#     else:
#         target_category = random.choice(['upper', 'lower'])
    
#     print("Target category:", target_category)  # Debug print
    
#     # Get recommendations with fresh randomization
#     target_path = os.path.join("static", "preprocessed", target_category)
#     available_images = []
#     used_items = set()  # Track used items
    
#     for root, _, files in os.walk(target_path):
#         for f in files:
#             if f.lower().endswith(('.png', '.jpg', '.jpeg')):
#                 img_path = os.path.join(root, f)
#                 if img_path not in used_items:  # Only add unused items
#                     available_images.append(img_path)
#                     used_items.add(img_path)
    
#     if not available_images:
#         return []
    
#     # Get fresh random recommendations
#     num_recommendations = min(6, len(available_images))
#     recommendations = random.sample(available_images, num_recommendations)
    
#     # Clear the random seed
#     random.seed()
    
#     return [rec.replace('\\', '/') for rec in recommendations]

# @app.route('/process')
# def process():
#     if not current_image_path or not os.path.exists(current_image_path):
#         flash("No image captured")
#         return redirect(url_for('camera'))
    
#     try:
#         recommendations = get_recommendations(current_image_path)
#         if not recommendations:
#             flash("No recommendations available")
#             return redirect(url_for('camera'))
        
#         # Get relative path for captured image
#         relative_path = os.path.relpath(current_image_path, BASE_DIR).replace("\\", "/")
        
#         return render_template('results.html', 
#                              input_img=relative_path,
#                              recommendations=recommendations)
                             
#     except Exception as e:
#         print(f"Error processing camera image: {str(e)}")
#         flash("Error processing image. Please try again.")
#         return redirect(url_for('results'))


# @app.route('/camera', methods=['GET'])
# def camera():
#     # Displays camera capture interface (see camera.html)
#     return render_template('camera.html')

@app.route('/logout')
def logout():
    if 'loggedin' in session:
        session.clear()  # Clear session only when user explicitly logs out
        # flash("You have been logged out!", "info")
    return redirect(url_for('home'))  # Redirect to home page instead of login

@app.errorhandler(500)
def internal_error(error):
    return "500 Internal Server Error. Please try again later.", 500


# ------------------ User Registration ------------------
@app.route('/register', methods=['POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name']
        username = request.form['username']
        email = request.form['email']
        phone_number = request.form['phone_number']
        password = request.form['password']

        # Check if user already exists
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM users WHERE username = %s OR email = %s OR phone_number = %s", 
                       (username, email, phone_number))
        existing_user = cursor.fetchone()

        if existing_user:
            flash("User already exists! Please try logging in.", "danger")
            return redirect(url_for('login_page'))  # Go to Login page
        
        # Hash the password before storing it
        password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

        # Insert new user into the database
        cursor.execute("""
            INSERT INTO users (full_name, username, email, phone_number, password_hash) 
            VALUES (%s, %s, %s, %s, %s)
        """, (full_name, username, email, phone_number, password_hash))

        mysql.connection.commit()
        cursor.close()

        flash("Registration successful!", "success")
        return redirect(url_for('option_page'))  # Redirect to recommend page

    return render_template('register.html')

# ------------------ User Login ------------------
@app.route('/login', methods=['POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT id, username, password_hash FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()

        # Check if user exists
        if not user:
            flash("Username not found! Please register first.", "danger")
            return redirect(url_for('register_page'))  # Go to register page

        # Check if password is correct
        if not bcrypt.check_password_hash(user['password_hash'], password):
            flash("Incorrect password! Please try again.", "danger")
            return redirect(url_for('login_page'))  # Stay on login page

        # Successful login, create session
        session['loggedin'] = True
        session['id'] = user['id']
        session['username'] = user['username']
        # flash("Login successful!", "success")
        return redirect(url_for('option_page'))  # Redirect to recommend page

    return render_template('login.html')


# ------------------ Run Flask App ------------------
if __name__ == '__main__':
    app.run(debug=True)

