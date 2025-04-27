---
👗 Fashion Recommendation System Using YOLOv8
---
This Flask web application processes a raw clothing dataset using a YOLOv8 model.
It segregates images into three categories — upper, lower, and full outfits — and logs approved images into a CSV file.
If an image contains both upper and lower detections, it is also copied for optional Siamese network training.
The recommendation engine uses cosine similarity and complementary color matching to suggest matching outfits.


---
🚀Features
---
1.YOLOv8 based clothing detection and classification

2.Siamese network for outfit similarity matching

3.User authentication (Login/Register pages)

4.Real-time upload and capture options

5.Image preprocessing and storage

6.CSV logging of processed images

7.Recommendation system for outfit suggestion

8.Organized folder structure and easy to extend

---
🗂️ Folder Structure
---

fashionnew/

│
├── Database(fashion_db)/

│   └── users.sql                      # SQL file to manage user data

│

├── preprocess_input/                  # Raw dataset

│   ├── test/

│   ├── valid/

│   └── data.yaml

│

├── static/                             # Static files (images, uploads, CSS)

│   ├── images/

│   ├── preprocessed/

│   │   ├── upper/

│   │   ├── lower/

│   │   └── full/

│   ├── siamese_train/

│   ├── uploads/

│   ├── approved_images.csv             # CSV log of approved images

│   └── styles.css                      # Custom CSS styling

│

├── templates/                          # Frontend templates (HTML)     

│   ├── index.html                      # Home page (upload/capture)

│   ├── login.html                      # Login page

│   ├── option.html                     # Option page (upload/capture choice)

│   ├── register.html                   # User registration page

│   ├── results.html                    # Display outfit recommendations

│

├── Training/                           # YOLOv8 training results and configs

│   ├── yolov8m_fashion/

│   ├── yolov8m_fashion_finetuning/

│   ├── yolov8m_fashion2/

│   ├── yolov8m_fashion3/

│   └── yolov8m_fashion4/

│


├── .gitattributes                      # For Git LFS (Large File Storage)

├── app.py                               # Main Flask application

├── preprocess.py                        # Image preprocessing script

├── recommendation_engine.py             # Recommendation system (similarity and matching)

├── requirements.txt                     # Python dependencies

├── siamese_model.pth                    # Trained Siamese network model (weights)

├── train_siamese.py                     # Siamese network training script

├── tempCodeRunnerFile.py                 # (temporary file - can be ignored)

└── README.md                             # Project documentation

---
🛠 Tech Stack
---
Frontend: HTML5, CSS3, JavaScript (basic)

Backend: Python, Flask

Machine Learning: YOLOv8 (for detection), Siamese Network (for similarity)

Database: SQL (for user management)

Storage: Git LFS (for large model files)

---
📸 Application Flow
---

User Login/Register → Upload/Capture Image → Preprocessing (YOLOv8) → 

Classify (Upper/Lower/Full) → Siamese Matching → 

Recommendation Results → Display Recommendations in website page
