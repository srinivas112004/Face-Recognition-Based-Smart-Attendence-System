import cv2
import os
from flask import Flask, request, render_template, jsonify, flash, redirect, url_for
from datetime import date, datetime
import numpy as np
from sklearn.neighbors import KNeighborsClassifier
import pandas as pd
import joblib
import json

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this to a random secret key

# Get the directory where this script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

nimgs = 10

# Initialize background image
if os.path.exists(os.path.join(BASE_DIR, "background.png")):
    imgBackground = cv2.imread(os.path.join(BASE_DIR, "background.png"))
else:
    imgBackground = None
    print("Warning: background.png not found. Using default background.")

datetoday = date.today().strftime("%m_%d_%y")
datetoday2 = date.today().strftime("%d-%B-%Y")


face_detector = cv2.CascadeClassifier(os.path.join(BASE_DIR, 'haarcascade_frontalface_default.xml'))

# Define paths relative to BASE_DIR
ATTENDANCE_DIR = os.path.join(BASE_DIR, 'Attendance')
STATIC_DIR = os.path.join(BASE_DIR, 'static')
FACES_DIR = os.path.join(STATIC_DIR, 'faces')

if not os.path.isdir(ATTENDANCE_DIR):
    os.makedirs(ATTENDANCE_DIR)
if not os.path.isdir(STATIC_DIR):
    os.makedirs(STATIC_DIR)
if not os.path.isdir(FACES_DIR):
    os.makedirs(FACES_DIR)
if f'Attendance-{datetoday}.csv' not in os.listdir(ATTENDANCE_DIR):
    with open(os.path.join(ATTENDANCE_DIR, f'Attendance-{datetoday}.csv'), 'w') as f:
        f.write('Name,Roll,Time')

def totalreg():
    return len(os.listdir(FACES_DIR))

def extract_faces(img):
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        face_points = face_detector.detectMultiScale(gray, 1.2, 5, minSize=(20, 20))
        return face_points
    except:
        return []

def identify_face(facearray):
    model = joblib.load(os.path.join(STATIC_DIR, 'face_recognition_model.pkl'))
    return model.predict(facearray)


def train_model():
    faces = []
    labels = []
    userlist = os.listdir(FACES_DIR)
    for user in userlist:
        for imgname in os.listdir(os.path.join(FACES_DIR, user)):
            img = cv2.imread(os.path.join(FACES_DIR, user, imgname))
            resized_face = cv2.resize(img, (50, 50))
            faces.append(resized_face.ravel())
            labels.append(user)
    faces = np.array(faces)
    knn = KNeighborsClassifier(n_neighbors=5)
    knn.fit(faces, labels)
    joblib.dump(knn, os.path.join(STATIC_DIR, 'face_recognition_model.pkl'))

def extract_attendance():
    df = pd.read_csv(os.path.join(ATTENDANCE_DIR, f'Attendance-{datetoday}.csv'))
    names = df['Name']
    rolls = df['Roll']
    times = df['Time']
    l = len(df)
    return names, rolls, times, l

def add_attendance(name):
    username = name.split('_')[0]
    userid = name.split('_')[1]
    current_time = datetime.now().strftime("%H:%M:%S")

    df = pd.read_csv(os.path.join(ATTENDANCE_DIR, f'Attendance-{datetoday}.csv'))
    
    # Check if user already marked attendance today
    if int(userid) not in list(df['Roll']):
        with open(os.path.join(ATTENDANCE_DIR, f'Attendance-{datetoday}.csv'), 'a') as f:
            f.write(f'\n{username},{userid},{current_time}')
        return True
    else:
        return False  # Already marked attendance

def getallusers():
    userlist = os.listdir(FACES_DIR)
    names = []
    rolls = []
    l = len(userlist)

    for i in userlist:
        name, roll = i.split('_')
        names.append(name)
        rolls.append(roll)

    return userlist, names, rolls, l


@app.route('/')
def home():
    names, rolls, times, l = extract_attendance()
    return render_template('home.html', names=names, rolls=rolls, times=times, l=l, totalreg=totalreg(), datetoday2=datetoday2)

@app.route('/api/stats')
def get_stats():
    """API endpoint to get attendance statistics"""
    names, rolls, times, l = extract_attendance()
    total_registered = totalreg()
    attendance_rate = (l / total_registered * 100) if total_registered > 0 else 0
    
    return jsonify({
        'present_today': l,
        'total_registered': total_registered,
        'attendance_rate': round(attendance_rate, 1),
        'date': datetoday2
    })

@app.route('/users')
def list_users():
    """Display all registered users"""
    userlist, names, rolls, l = getallusers()
    return render_template('users.html', userlist=userlist, names=names, rolls=rolls, l=l, datetoday2=datetoday2)

@app.route('/delete_user/<username>')
def delete_user(username):
    """Delete a user from the system"""
    try:
        user_folder = os.path.join(FACES_DIR, username)
        if os.path.exists(user_folder):
            import shutil
            shutil.rmtree(user_folder)
            # Retrain model after deletion
            if totalreg() > 0:
                train_model()
            flash(f'User {username} has been successfully deleted!', 'success')
        else:
            flash(f'User {username} not found!', 'error')
    except Exception as e:
        flash(f'Error deleting user: {str(e)}', 'error')
    
    return redirect(url_for('list_users'))

@app.route('/start', methods=['GET'])
def start():
    names, rolls, times, l = extract_attendance()

    if 'face_recognition_model.pkl' not in os.listdir(STATIC_DIR):
        flash('There is no trained model in the static folder. Please add a new face to continue.', 'error')
        return redirect(url_for('home'))

    try:
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            flash('Could not access camera. Please check camera permissions.', 'error')
            return redirect(url_for('home'))
        
        # Variables to control attendance capture
        attendance_taken = False
        face_detected_frames = 0
        required_frames = 30  # Number of consecutive frames to confirm face detection
        max_frames = 300  # Maximum frames to prevent infinite loop (10 seconds at 30fps)
        frame_count = 0
        last_identified_person = None
        
        while frame_count < max_frames and not attendance_taken:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            faces = extract_faces(frame)
            
            if len(faces) > 0:
                (x, y, w, h) = faces[0]
                # Draw rectangle around face
                cv2.rectangle(frame, (x, y), (x+w, y+h), (86, 32, 251), 2)
                cv2.rectangle(frame, (x, y-40), (x+w, y), (86, 32, 251), -1)
                
                face = cv2.resize(frame[y:y+h, x:x+w], (50, 50))
                identified_person = identify_face(face.reshape(1, -1))[0]
                
                # Check if same person detected in consecutive frames
                if identified_person == last_identified_person:
                    face_detected_frames += 1
                else:
                    face_detected_frames = 1
                    last_identified_person = identified_person
                
                # Display name on frame
                cv2.putText(frame, f'{identified_person}', (x, y-15), 
                           cv2.FONT_HERSHEY_COMPLEX, 0.8, (255, 255, 255), 2)
                
                # Show detection progress
                progress = min(face_detected_frames / required_frames * 100, 100)
                cv2.putText(frame, f'Recognition: {progress:.1f}%', (30, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # Take attendance if face detected consistently
                if face_detected_frames >= required_frames:
                    attendance_success = add_attendance(identified_person)
                    if attendance_success:
                        attendance_taken = True
                        
                        # Show success message on frame
                        cv2.putText(frame, 'ATTENDANCE RECORDED!', (30, 60),
                                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
                        cv2.putText(frame, f'Welcome {identified_person.split("_")[0]}!', (30, 90),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                    else:
                        # Already marked attendance
                        cv2.putText(frame, 'ALREADY MARKED TODAY!', (30, 60),
                                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 165, 255), 3)
                        cv2.putText(frame, f'Hi {identified_person.split("_")[0]}!', (30, 90),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)
                        attendance_taken = True  # Stop camera even if already marked
                    
            else:
                face_detected_frames = 0
                last_identified_person = None
                cv2.putText(frame, 'Looking for faces...', (30, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # Instructions for user
            cv2.putText(frame, 'Press ESC to exit', (30, frame.shape[0] - 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            # Display frame
            if imgBackground is not None and frame.shape[0] <= 480 and frame.shape[1] <= 640:
                imgBackground[162:162 + frame.shape[0], 55:55 + frame.shape[1]] = frame
                cv2.imshow('Attendance System', imgBackground)
            else:
                cv2.imshow('Attendance System', frame)
            
            # Check for ESC key or if attendance was taken
            key = cv2.waitKey(1) & 0xFF
            if key == 27 or attendance_taken:  # ESC key or attendance taken
                if attendance_taken:
                    # Show success message for a moment
                    cv2.waitKey(2000)  # Wait 2 seconds to show success message
                break
                
    except Exception as e:
        flash(f'Error during face recognition: {str(e)}', 'error')
    finally:
        cap.release()
        cv2.destroyAllWindows()
    
    if attendance_taken and last_identified_person:
        username = last_identified_person.split("_")[0]
        # Check if it was a new attendance or already marked
        df = pd.read_csv(os.path.join(ATTENDANCE_DIR, f'Attendance-{datetoday}.csv'))
        userid = int(last_identified_person.split("_")[1])
        if userid in list(df['Roll']):
            # Check if this was just added (last entry)
            if len(df) > 0 and df.iloc[-1]['Roll'] == userid:
                flash(f'Attendance recorded successfully for {username}!', 'success')
            else:
                flash(f'Welcome back {username}! You have already marked attendance today.', 'info')
        else:
            flash(f'Attendance recorded successfully for {username}!', 'success')
    else:
        flash('No face detected or attendance recording failed. Please try again.', 'warning')
    
    return redirect(url_for('home'))



@app.route('/add', methods=['GET', 'POST'])
def add():
    if request.method == 'GET':
        return render_template('add_user.html', datetoday2=datetoday2)
    
    newusername = request.form['newusername']
    newuserid = request.form['newuserid']
    
    # Validate input
    if not newusername or not newuserid:
        flash('Please fill in all fields!', 'error')
        return redirect(url_for('home'))
    
    # Check if user already exists
    userlist, names, rolls, l = getallusers()
    if newuserid in rolls:
        flash(f'User ID {newuserid} already exists!', 'error')
        return redirect(url_for('home'))
    
    userimagefolder = os.path.join(FACES_DIR, newusername + '_' + str(newuserid))
    if not os.path.isdir(userimagefolder):
        os.makedirs(userimagefolder)
    
    try:
        i, j = 0, 0
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            flash('Could not access camera. Please check camera permissions.', 'error')
            return redirect(url_for('home'))
        
        flash(f'Camera opened. Please look at the camera. Capturing {nimgs} images...', 'info')
        
        while i < nimgs:
            ret, frame = cap.read()
            if not ret:
                break
                
            faces = extract_faces(frame)
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 20), 2)
                cv2.putText(frame, f'Images Captured: {i}/{nimgs}', (30, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 20), 2, cv2.LINE_AA)
                if j % 5 == 0:
                    name = newusername+'_'+str(i)+'.jpg'
                    cv2.imwrite(os.path.join(userimagefolder, name), frame[y:y+h, x:x+w])
                    i += 1
                j += 1
            
            cv2.imshow('Adding new User', frame)
            if cv2.waitKey(1) == 27:  # ESC key
                break
                
        cap.release()
        cv2.destroyAllWindows()
        
        if i < nimgs:
            flash(f'Only captured {i} images. Please try again.', 'warning')
        else:
            print('Training Model...')
            train_model()
            flash(f'User {newusername} has been successfully registered!', 'success')
            
    except Exception as e:
        flash(f'Error during user registration: {str(e)}', 'error')
    
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
