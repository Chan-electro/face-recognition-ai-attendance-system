# Face Recognition Attendance System with AI Assistant

A comprehensive Flask-based attendance management system featuring face recognition, an integrated lightweight AI assistant, and role-based dashboards for Students, Teachers, and Admins.

## 🎯 Features

### Core Functionality
- ✅ **Face Recognition Attendance**: Automatic attendance marking using OpenCV and face_recognition library
- ✅ **AI Assistant**: Lightweight SentenceTransformers-based Q&A system for student queries
- ✅ **Three Role-Based Portals**: Student, Teacher, and Admin dashboards
- ✅ **Pure HTML/CSS/JS Frontend**: Bootstrap 5 with Material Icons
- ✅ **Attendance Analytics**: Subject-wise breakdown, percentage calculations, improvement suggestions
- ✅ **Report Generation**: CSV and PDF export capabilities

### Student Portal
- View overall and subject-wise attendance
- AI chatbot for academic queries (subjects, faculty, timetable, policies)
- Attendance improvement suggestions
- Class timetable viewing
- Subject and faculty information

### Teacher Portal
- Face recognition-based attendance marking
- Manual attendance override
- Student facial data management
- Class attendance reports
- Student attendance patterns

### Admin Portal
- User management (add/remove students and teachers)
- Timetable management
- AI training data upload and model retraining
- System configuration
- Faculty and subject management

## 🛠️ Technology Stack

### Backend
- **Framework**: Flask 3.0.0
- **Database**: SQLite (easily upgradeable to PostgreSQL/MySQL)
- **ORM**: SQLAlchemy

### AI & Machine Learning
- **AI Model**: SentenceTransformers (all-MiniLM-L6-v2) - 80MB, CPU-optimized
- **Face Recognition**: face_recognition library with dlib
- **Computer Vision**: OpenCV

### Frontend
- **HTML5, CSS3, JavaScript (Vanilla)**
- **UI Framework**: Bootstrap 5
- **Icons**: Material Icons
- **Charts**: Chart.js

## 📋 Prerequisites

- Python 3.8 or higher
- Webcam (for face recognition)
- 4GB RAM minimum
- Modern web browser (Chrome, Firefox, Safari, Edge)

## 🚀 Installation

### 1. Clone or Navigate to Project Directory

```bash
cd "/Users/joyrajroy/Chandan/Inchara Project"
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate  # On Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

**Note**: Installing `dlib` and `face_recognition` might take some time. If you encounter issues:
- On macOS: `brew install cmake`
- On Ubuntu: `sudo apt-get install cmake libboost-all-dev`
- On Windows: Install Visual Studio C++ Build Tools

### 4. Initialize Database

The database will be automatically initialized on first run with seed data.

### 5. Run the Application

```bash
python app.py
```

The application will be available at: **http://localhost:5000**

## 🔐 Default Credentials

### Admin
- **Username**: admin
- **Password**: admin123

### Teacher
- **Username**: teacher1 or teacher2
- **Password**: teacher123

### Student
- **Username**: student1, student2, student3, student4, student5
- **Password**: student123

## 📂 Project Structure

```
Inchara Project/
├── app.py                          # Main Flask application
├── config.py                       # Configuration settings
├── requirements.txt                # Python dependencies
│
├── models/                         # Database models
│   ├── user.py                     # User model
│   ├── attendance.py               # Attendance records
│   ├── face_encoding.py            # Facial embeddings
│   ├── subject.py                  # Subjects
│   ├── faculty.py                  # Faculty information
│   └── timetable.py                # Class schedule
│
├── controllers/                    # Route handlers
│   ├── auth_controller.py          # Authentication
│   ├── student_controller.py       # Student portal
│   ├── teacher_controller.py       # Teacher portal
│   ├── admin_controller.py         # Admin portal
│   └── ai_controller.py            # AI API endpoints
│
├── services/                       # Business logic
│   ├── ai_service.py               # AI model & inference
│   ├── face_recognition_service.py # Face detection & matching
│   ├── attendance_service.py       # Attendance calculations
│   └── report_service.py           # Report generation
│
├── utils/                          # Utility functions
│   ├── auth_utils.py               # Authentication decorators
│   ├── db_utils.py                 # Database helpers
│   └── file_utils.py               # File operations
│
├── templates/                      # HTML templates
│   ├── base.html                   # Base template
│   ├── login.html                  # Login page
│   ├── student/                    # Student portal templates
│   ├── teacher/                    # Teacher portal templates
│   └── admin/                      # Admin portal templates
│
├── static/                         # Frontend assets
│   ├── css/                        # Stylesheets
│   └── js/                         # JavaScript files
│
└── data/                           # Application data
    ├── ai_training/                # AI training datasets
    ├── face_images/                # Facial images
    └── exports/                    # Generated reports
```

## 🤖 AI Assistant

### How It Works

The AI assistant uses **SentenceTransformers** to understand questions semantically:

1. **Training Data**: FAQs, subject info, policies stored in `/data/ai_training/`
2. **Embeddings**: Questions are converted to 384-dimensional vectors
3. **Matching**: User questions are matched using cosine similarity
4. **Response**: Best matching answer is returned with confidence score

### Adding Training Data

1. Login as **Admin**
2. Go to **AI Training** page
3. Upload CSV files with format:
   ```csv
   question,answer,category
   "Who teaches AI?","Dr. Smith teaches AI",faculty
   ```
4. Click **Retrain AI Model**

## 📸 Face Recognition

### How It Works

1. **Enrollment**: Teacher captures student's face → System generates 128-D encoding
2. **Attendance**: Teacher captures face → System matches against stored encodings
3. **Verification**: Confidence score must be above threshold (default 60%)
4. **Fallback**: Manual attendance marking available

### Adding Student Faces

1. Login as **Teacher**
2. Go to **Manage Faces**
3. Select student
4. Capture face image
5. System automatically stores encoding

## 📊 Attendance Management

### Features

- **Real-time Tracking**: Instant attendance percentage updates
- **Subject-wise Breakdown**: Per-subject attendance analytics
- **Improvement Suggestions**: Calculates required classes for target percentage
- **Status Alerts**: Warnings for below 75% attendance
- **Export Options**: CSV and PDF reports

### Attendance Formula

```
Attendance % = (Present + Late) / Total Classes × 100
```

## 🎨 UI/UX Features

- ✅ Responsive design (mobile-friendly)
- ✅ Material Design icons
- ✅ Chart.js visualizations
- ✅ Real-time form validation
- ✅ Toast notifications
- ✅ Loading states
- ✅ Clean, modern interface

## ⚙️ Configuration

Edit `config.py` for customization:

```python
# Attendance settings
MINIMUM_ATTENDANCE_PERCENTAGE = 75
LATE_THRESHOLD_MINUTES = 10

# Face recognition
FACE_DETECTION_MODEL = 'hog'  # 'hog' for CPU, 'cnn' for GPU
FACE_RECOGNITION_TOLERANCE = 0.6  # Lower = more strict

# AI settings
AI_MODEL_NAME = 'all-MiniLM-L6-v2'
AI_CONFIDENCE_THRESHOLD = 0.5
```

## 🧪 Testing

### Face Recognition
1. Use good lighting
2. Face should be clearly visible
3. Look directly at camera
4. Avoid glasses/masks for better accuracy

### AI Assistant Sample Questions
- "Who teaches Data Structures?"
- "What is the minimum attendance required?"
- "When is the Operating Systems class?"
- "How can I improve my attendance?"

## 📈 Performance

- **AI Response Time**: <100ms per query
- **Face Recognition**: ~500ms per capture
- **Model Size**: ~80MB (SentenceTransformers)
- **Database**: SQLite (supports 1000+ students)

## 🔧 Troubleshooting

### Camera not working
- Grant browser camera permissions
- Check if camera is in use by another application
- Try different browser

### Face recognition fails
- Ensure good lighting
- Face should be centered and clear
- Check if face encoding exists for student
- Use manual attendance as fallback

### AI not responding
- Check if model is trained (Admin → AI Training)
- Verify training data files exist in `/data/ai_training/`
- Check console for errors

### Database errors
- Delete `database/attendance.db` and restart app
- Database will be recreated with seed data

## 🚀 Deployment

For production deployment:

1. Change `SECRET_KEY` in `config.py`
2. Use production WSGI server (Gunicorn, uWSGI)
3. Set up proper database (PostgreSQL/MySQL)
4. Enable HTTPS
5. Configure firewall rules

Example with Gunicorn:
```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:create_app()
```

## 📝 License

This project is created for educational purposes.

## 🤝 Support

For issues or questions:
1. Check the troubleshooting section
2. Review the code documentation
3. Check browser console for errors

## 🎓 Credits

- **Face Recognition**: face_recognition library by Adam Geitgey
- **AI Model**: SentenceTransformers by UKPLab
- **UI Framework**: Bootstrap 5
- **Icons**: Google Material Icons

---

**Built with ❤️ using Flask, OpenCV, and AI**
