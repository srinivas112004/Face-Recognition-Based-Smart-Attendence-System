# Face Recognition Attendance System 🎯

## 📋 Project Overview
A modern, professional Flask-based web application that uses advanced face recognition technology to automate attendance tracking. The system features a sleek UI, intelligent face detection, and automatic attendance recording with smart camera controls.

## 🌟 Key Highlights
- **Admin Authentication & RBAC**: Secure login portal with password hashing protecting administrative features
- **Modern UI/UX**: Professional glass-morphism design with Dark & Light theme switcher
- **Dual Punch System**: Intelligent Check-In and Check-Out with total duration tracking
- **Late vs. On-Time Tagging**: Automatic status badge evaluation against customizable cutoff time
- **Absentee Tracking & Manual Override**: Instant identification of absent users with 1-click manual "Present" or "On Leave" marking
- **Individual Student Profiles**: Comprehensive attendance history page for each student with consistency tracking
- **System Settings Configuration**: Custom Organization Name and Cutoff Time editable directly from UI (`config.json`)
- **Historical Attendance Viewer**: Integrated date picker to review and query past records
- **One-Click CSV Export**: Download attendance reports for today or any historical date
- **Voice & Audio Feedback**: Browser Text-to-Speech greeting and synthesized confirmation chimes
- **Instant Live Search**: Real-time filtering across attendance and registered user tables
- **Intelligent Recognition**: Progressive face detection with confidence tracking
- **User Management**: Complete CRUD operations for user management and automatic model retraining

## 🚀 Enhanced Features

### 🎨 **UI/UX Improvements**
- **Modern Design System**: Purple-blue gradient theme with glass-morphism effects
- **Responsive Layout**: Bootstrap 5.3 with mobile-first approach
- **Interactive Dashboard**: Real-time statistics with animated elements
- **Professional Navigation**: Fixed navbar with branded design
- **Enhanced Typography**: Google Fonts (Poppins) for better readability
- **Smooth Animations**: CSS transitions and keyframe animations

### 🧠 **Smart Attendance System**
- **Auto-Stop Camera**: Automatically closes camera after attendance recording
- **Progressive Recognition**: Requires 30 consecutive frames for accuracy
- **Duplicate Prevention**: Prevents multiple attendance entries per day
- **Visual Feedback**: Real-time recognition progress and status messages
- **Error Handling**: Graceful camera failure and error recovery
- **Timeout Protection**: Maximum 10-second camera session to prevent hanging

### 👥 **User Management**
- **User Dashboard**: View all registered users with profile avatars
- **Delete Users**: Remove users with confirmation dialogs
- **Registration Flow**: Enhanced user registration with better feedback
- **Statistics Tracking**: Attendance rate calculation and metrics
- **Profile Display**: User cards with visual indicators

### 📱 **Mobile Experience**
- **Touch-Friendly**: Large buttons and touch targets
- **Responsive Tables**: Horizontal scrolling for mobile devices
- **Optimized Forms**: Mobile-friendly input fields
- **Progressive Enhancement**: Works on all devices

## 🛠️ Technology Stack
- **Backend**: Flask 2.3.3 (Python)
- **Face Detection**: OpenCV 4.12 with Haar Cascade Classifier
- **Machine Learning**: scikit-learn 1.7.1 (K-Nearest Neighbors)
- **Data Processing**: Pandas 2.3.1, NumPy 2.2.6
- **Frontend**: HTML5, CSS3, Bootstrap 5.3
- **Icons**: Font Awesome 6.4, Material Icons
- **JavaScript**: ES6+ with modern browser APIs

## 📦 Dependencies
```bash
Flask==2.3.3
opencv-python==4.12.0.88
numpy==2.2.6
scikit-learn==1.7.1
pandas==2.3.1
joblib==1.5.1
waitress==3.0.0
gunicorn==21.2.0
```

## 🔧 Installation & Setup

### **Quick Start** ⚡
1. **Clone/Download** the project
2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Run Application**:
   ```bash
   python app.py
   ```
4. **Access Dashboard**:
   - Local: `http://127.0.0.1:5000`
   - Network: `http://[your-ip]:5000`

### **Production Deployment** 🌐
```bash
# Using Waitress (Windows)
waitress-serve --port=5000 app:app

# Using Gunicorn (Linux/Mac)
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## 📁 Enhanced Project Structure
```
Face-Recognition-Based-Smart-Attendence-System/
├── app.py                              # 🚀 Main Flask application
├── config.json                         # ⚙️ System configuration (Admin, Cutoff time, Org name)
├── users_auth.json                     # 🔑 User/Student authentication credentials
├── background.png                      # 🎨 UI background image
├── haarcascade_frontalface_default.xml # 👤 OpenCV Face detection cascade model
├── requirements.txt                    # 📦 Python dependencies
├── README.md                          # 📖 Documentation
├── .gitignore                         # 🙈 Git ignore rules
├── Attendance/                        # 📊 Daily attendance CSV files
│   ├── .gitkeep
│   └── Attendance-[MM_DD_YY].csv     
├── static/                           # 🗂️ Static assets
│   ├── faces/                        # 👥 Enrolled facial samples
│   │   └── [username_id]/            
│   └── face_recognition_model.pkl    # 🧠 Trained KNN ML model
└── templates/                        # 🌐 HTML templates
    ├── home.html                     # 🏠 Modern dashboard with live stats & tabs
    ├── login.html                    # 🔐 Dual role login (Admin & Student)
    ├── users.html                    # 👥 User management portal
    ├── user_profile.html             # 👤 Student attendance history & self-service
    └── add_user.html                 # ➕ User registration template
```

## 🚀 Pushing to GitHub

To push this repository to your GitHub account:

```bash
# 1. Add your GitHub repository remote URL
git remote add origin https://github.com/<your-username>/<your-repo-name>.git

# 2. Rename branch to main
git branch -M main

# 3. Push to GitHub
git push -u origin main
```

## 📖 How to Use

### **🆕 Adding New Users**
1. Navigate to the **main dashboard**
2. Fill in the **"Add New User"** form:
   - Enter **Full Name** (e.g., "John Doe")
   - Enter **User ID** (unique number)
3. Click **"Register New User"**
4. **Camera opens automatically** for face capture
5. **Look at camera** - system captures 10 images
6. **Model trains automatically** with new data
7. **Success confirmation** displayed

### **📸 Smart Attendance Capture**
1. Click **"Start Attendance Capture"** on dashboard
2. **Camera activates** with live preview
3. **Position face** in camera view
4. **Recognition progress** shown in real-time
5. **Attendance automatically recorded** after consistent detection
6. **Camera stops automatically** - no manual intervention needed
7. **Success message** confirms attendance recording

### **👥 User Management**
1. Click **"Manage Users"** in navigation
2. **View all registered users** with profile cards
3. **Delete users** with confirmation dialogs
4. **Automatic model retraining** after user deletion

### **📊 Dashboard Features**
- **Live Statistics**: Present today, total registered, attendance rate
- **Real-time Updates**: Auto-refresh every 30 seconds
- **Attendance Table**: Sortable table with user avatars
- **Status Indicators**: Visual feedback for all operations

## ⚙️ System Configuration

### **Smart Camera Settings**
- **Recognition Threshold**: 30 consecutive frames
- **Maximum Session**: 300 frames (10 seconds)
- **Auto-Stop**: Enabled after successful detection
- **Duplicate Prevention**: One attendance per day per user

### **ML Model Configuration**
- **Algorithm**: K-Nearest Neighbors (k=5)
- **Face Resolution**: 50x50 pixels
- **Training Images**: 10 per user
- **Auto-Training**: Triggered on user add/delete

### **UI/UX Settings**
- **Theme**: Modern gradient design
- **Animations**: Smooth transitions enabled
- **Responsive**: Mobile-first approach
- **Accessibility**: High contrast, readable fonts

## 📊 Data Management

### **Attendance Records** 📈
- **Format**: CSV files organized by date
- **Location**: `Attendance/Attendance-[MM_DD_YY].csv`
- **Columns**: Name, Roll (ID), Time
- **Auto-Creation**: New files created daily
- **Duplicate Prevention**: One entry per user per day

### **Face Data Storage** 👤
- **Organization**: `static/faces/[username_id]/`
- **Images per User**: 10 training images
- **Format**: JPG files with sequential naming
- **Auto-Cleanup**: Removed when user is deleted

### **Model Persistence** 🧠
- **File**: `static/face_recognition_model.pkl`
- **Auto-Training**: Triggered on data changes
- **Algorithm**: scikit-learn KNN classifier
- **Backup**: Manual backup recommended

## 🎯 API Endpoints

### **Public Routes**
- `GET /` - Main dashboard
- `GET /users` - User management page
- `GET /start` - Start attendance capture
- `POST /add` - Add new user
- `GET /delete_user/<username>` - Delete user

### **API Routes**
- `GET /api/stats` - JSON statistics endpoint

## 🐛 Troubleshooting Guide

### **Camera Issues** 📷
| Problem | Solution |
|---------|----------|
| Camera won't open | Check if another app is using webcam |
| Poor face detection | Ensure good lighting conditions |
| Camera doesn't stop | Fixed with auto-stop feature |
| Permission denied | Grant camera permissions to browser |

### **Recognition Issues** 🤖
| Problem | Solution |
|---------|----------|
| Face not recognized | Add more training images |
| False positives | Increase recognition threshold |
| Model not found | Add at least one user first |
| Low accuracy | Ensure consistent lighting during training |

### **Application Issues** 💻
| Problem | Solution |
|---------|----------|
| Port already in use | Change port in app.py or kill other process |
| Dependencies missing | Run `pip install -r requirements.txt` |
| Static files not loading | Check file permissions and paths |
| Database errors | Ensure Attendance folder exists |

## 🔐 Security & Dual Authentication

### **Role-Based Access Control (RBAC)** 🛡️
- **Admin Portal**:
  - **Credentials**: `admin` / `admin123`
  - **Capabilities**: Enroll faces, retrain models, delete users, configure cutoff times, manual override, reset records, and export reports.
- **Student / Employee Self-Service Portal**:
  - **Credentials**:
    - **User ID**: Student's Roll ID (e.g., `1`, `10`, `101`)
    - **Password**: User's Roll ID (or `user123` by default)
  - **Capabilities**: View personal attendance history, punch-in/out log, attendance rate percentage, and change personal account password.
  - **Privacy Protected**: Students can only view their own attendance records; access to administrative management is strictly forbidden.
- **Password Security**: Passwords are cryptographically hashed using Werkzeug (`scrypt` / `pbkdf2`) and stored in `users_auth.json`.
- **Public Kiosk Mode**: The main live attendance board and facial recognition scanner (`/start`) remain hands-free and open for entrance terminals.

## 🚀 Future Enhancements

### **Planned Features** 🔮
- [ ] **Multi-camera Support**: Support for multiple camera inputs
- [ ] **Database Integration**: PostgreSQL/MySQL integration
- [ ] **REST API**: Complete RESTful API with authentication
- [ ] **Mobile App**: React Native mobile application
- [ ] **Cloud Storage**: AWS S3 integration for face data
- [ ] **Analytics**: Advanced reporting and analytics dashboard
- [ ] **LDAP Integration**: Active Directory integration
- [ ] **Email Notifications**: Automated attendance reports

### **Technical Improvements** ⚙️
- [ ] **Docker Support**: Containerization for easy deployment
- [ ] **Redis Caching**: Performance optimization
- [ ] **WebSocket Support**: Real-time updates
- [ ] **Progressive Web App**: PWA capabilities
- [ ] **Multi-language**: Internationalization support

## 📝 Changelog

### **Version 2.0** (October 2025) - Current
- ✅ Complete UI/UX redesign with modern aesthetics
- ✅ Smart camera auto-stop functionality
- ✅ Progressive face recognition system
- ✅ User management dashboard
- ✅ Mobile responsive design
- ✅ Enhanced error handling and user feedback
- ✅ Real-time statistics and metrics

### **Version 1.0** (Original)
- ✅ Basic face recognition attendance system
- ✅ Simple web interface
- ✅ CSV-based data storage
- ✅ Manual camera control

## 🤝 Contributing
This is an open-source project. Contributions are welcome!

1. **Fork** the repository
2. **Create** feature branch (`git checkout -b feature/AmazingFeature`)
3. **Commit** changes (`git commit -m 'Add AmazingFeature'`)
4. **Push** to branch (`git push origin feature/AmazingFeature`)
5. **Open** Pull Request

## � License
This project is open source and available under the [MIT License](LICENSE).

## 👨‍💻 Developer Information
- **Last Updated**: October 4, 2025
- **Python Version**: 3.10+
- **Status**: ✅ Fully Functional & Production Ready
- **Maintainer**: [Your Name]
- **Support**: Issues and feature requests welcome

## 🙏 Acknowledgments
- OpenCV community for computer vision libraries
- Flask development team for the web framework
- scikit-learn for machine learning capabilities
- Bootstrap team for responsive UI components

---

### 📞 Support & Contact
For technical support or feature requests, please open an issue on the repository.

**Happy Coding! 🎉**
