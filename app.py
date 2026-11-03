import cv2
import os
from flask import Flask, request, render_template, jsonify, flash, redirect, url_for, send_file, session
from datetime import date, datetime
import numpy as np
from sklearn.neighbors import KNeighborsClassifier
import pandas as pd
import joblib
import json
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'smart-face-attendance-secret-key-change-in-prod'

# Get the directory where this script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

nimgs = 10

# Configuration Management
CONFIG_FILE = os.path.join(BASE_DIR, 'config.json')
USERS_AUTH_FILE = os.path.join(BASE_DIR, 'users_auth.json')

DEFAULT_CONFIG = {
    'org_name': 'FaceAttend Pro',
    'cutoff_time': '09:30:00',
    'auto_camera_timeout': 10,
    'admin_username': 'admin',
    'admin_password': 'admin123'
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        except Exception:
            return DEFAULT_CONFIG
    return DEFAULT_CONFIG

def save_config(cfg):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(cfg, f, indent=4)
        return True
    except Exception:
        return False

def load_user_auth():
    if os.path.exists(USERS_AUTH_FILE):
        try:
            with open(USERS_AUTH_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_user_auth(auth_data):
    try:
        with open(USERS_AUTH_FILE, 'w') as f:
            json.dump(auth_data, f, indent=4)
        return True
    except Exception:
        return False

def check_admin_credentials(username, password):
    cfg = load_config()
    cfg_user = cfg.get('admin_username', 'admin')
    cfg_pwd = cfg.get('admin_password', 'admin123')
    
    if username != cfg_user:
        return False
        
    if str(cfg_pwd).startswith('pbkdf2:') or str(cfg_pwd).startswith('scrypt:'):
        return check_password_hash(cfg_pwd, password)
    else:
        return str(cfg_pwd) == password

def check_user_credentials(user_id, password):
    """
    Validates a student/user's credentials.
    Default password for any registered user is their User ID or 'user123'.
    Custom passwords set by the user are stored in users_auth.json.
    """
    user_id_str = str(user_id).strip()
    userlist, names, rolls, total = getallusers()
    
    user_name = None
    for i in range(total):
        if str(rolls[i]).strip() == user_id_str:
            user_name = names[i]
            break
            
    if not user_name:
        return False, None
        
    auth_data = load_user_auth()
    if user_id_str in auth_data:
        saved_pwd = auth_data[user_id_str].get('password', '')
        if str(saved_pwd).startswith('pbkdf2:') or str(saved_pwd).startswith('scrypt:'):
            if check_password_hash(saved_pwd, password):
                return True, user_name
        elif saved_pwd == password:
            return True, user_name
    else:
        # Default accepted passwords: user's Roll ID or 'user123'
        if password == user_id_str or password == 'user123':
            return True, user_name
            
    return False, None

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Administrator login required to access this feature.', 'warning')
            return redirect(url_for('login', next=request.url))
        if session.get('role') != 'admin':
            flash('Administrator privileges required.', 'error')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Please log in to continue.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Initialize background image
if os.path.exists(os.path.join(BASE_DIR, "background.png")):
    imgBackground = cv2.imread(os.path.join(BASE_DIR, "background.png"))
else:
    imgBackground = None
    print("Warning: background.png not found. Using default background.")

def get_datetoday():
    return date.today().strftime("%m_%d_%y")

def get_datetoday2():
    return date.today().strftime("%d-%B-%Y")

def format_date_for_display(date_obj):
    return date_obj.strftime("%d-%B-%Y")

def date_to_str(date_obj):
    return date_obj.strftime("%m_%d_%y")

def parse_date_query(date_str):
    """Parses 'YYYY-MM-DD' or 'MM_DD_YY' into a datetime.date object, defaulting to today."""
    if not date_str:
        return date.today()
    date_str = str(date_str).strip()
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        try:
            return datetime.strptime(date_str, "%m_%d_%y").date()
        except ValueError:
            return date.today()

def calculate_duration(t_in_str, t_out_str):
    """Calculates human-readable duration between two HH:MM:SS timestamps."""
    try:
        t_in = datetime.strptime(str(t_in_str).strip(), "%H:%M:%S")
        t_out = datetime.strptime(str(t_out_str).strip(), "%H:%M:%S")
        diff = t_out - t_in
        total_seconds = int(diff.total_seconds())
        if total_seconds < 0:
            return "0m"
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        if hours > 0:
            return f"{hours}h {minutes}m"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    except Exception:
        return "-"

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

initial_attendance_file = os.path.join(ATTENDANCE_DIR, f'Attendance-{get_datetoday()}.csv')
if not os.path.exists(initial_attendance_file):
    with open(initial_attendance_file, 'w') as f:
        f.write('Name,Roll,Time,CheckOut,Duration,Status\n')

def totalreg():
    if not os.path.isdir(FACES_DIR):
        return 0
    return len([d for d in os.listdir(FACES_DIR) if os.path.isdir(os.path.join(FACES_DIR, d))])

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
    userlist = [u for u in os.listdir(FACES_DIR) if os.path.isdir(os.path.join(FACES_DIR, u))]
    for user in userlist:
        user_dir = os.path.join(FACES_DIR, user)
        for imgname in os.listdir(user_dir):
            img = cv2.imread(os.path.join(user_dir, imgname))
            if img is not None:
                resized_face = cv2.resize(img, (50, 50))
                faces.append(resized_face.ravel())
                labels.append(user)
    if len(faces) == 0:
        model_path = os.path.join(STATIC_DIR, 'face_recognition_model.pkl')
        if os.path.exists(model_path):
            os.remove(model_path)
        return
    faces = np.array(faces)
    n_neighbors = min(5, len(faces))
    knn = KNeighborsClassifier(n_neighbors=n_neighbors)
    knn.fit(faces, labels)
    joblib.dump(knn, os.path.join(STATIC_DIR, 'face_recognition_model.pkl'))

def extract_attendance(target_date=None):
    """
    Extracts attendance for a given date.
    Backward-compatible with older 3-column CSV files.
    """
    if target_date is None:
        target_date = date.today()
    date_code = date_to_str(target_date)
    attendance_file = os.path.join(ATTENDANCE_DIR, f'Attendance-{date_code}.csv')
    
    expected_columns = ['Name', 'Roll', 'Time', 'CheckOut', 'Duration', 'Status']
    cfg = load_config()
    cutoff_time = cfg.get('cutoff_time', '09:30:00')

    if not os.path.exists(attendance_file):
        if target_date == date.today():
            with open(attendance_file, 'w') as f:
                f.write(','.join(expected_columns) + '\n')
        else:
            return [], [], [], [], [], [], 0

    try:
        df = pd.read_csv(attendance_file)
    except Exception:
        return [], [], [], [], [], [], 0

    if 'Name' not in df.columns or len(df) == 0:
        return [], [], [], [], [], [], 0

    if 'Roll' not in df.columns:
        df['Roll'] = '0'
    if 'Time' not in df.columns:
        df['Time'] = '-'
    if 'CheckOut' not in df.columns:
        df['CheckOut'] = '-'
    if 'Duration' not in df.columns:
        df['Duration'] = '-'
    if 'Status' not in df.columns:
        def compute_status(t_val):
            try:
                t_str = str(t_val).strip()
                if t_str != '-' and t_str:
                    return 'On Time' if t_str <= cutoff_time else 'Late'
            except Exception:
                pass
            return 'On Time'
        df['Status'] = df['Time'].apply(compute_status)

    # Clean missing / NaN values
    df['CheckOut'] = df['CheckOut'].fillna('-').astype(str)
    df['Duration'] = df['Duration'].fillna('-').astype(str)
    df['Status'] = df['Status'].fillna('On Time').astype(str)
    df['Time'] = df['Time'].fillna('-').astype(str)
    df['Roll'] = df['Roll'].fillna('0').astype(str)
    df['Name'] = df['Name'].fillna('Unknown').astype(str)

    names = list(df['Name'])
    rolls = list(df['Roll'])
    times = list(df['Time'])
    checkouts = list(df['CheckOut'])
    durations = list(df['Duration'])
    statuses = list(df['Status'])
    l = len(df)
    return names, rolls, times, checkouts, durations, statuses, l

def add_attendance(name):
    """
    Handles both Check-In and Check-Out.
    1st scan: Check-In (records entry time and calculates On-Time / Late status)
    2nd scan: Check-Out (records exit time and calculates duration)
    3rd scan+: Informs that attendance has already been completed today.
    """
    parts = name.rsplit('_', 1)
    username = parts[0]
    userid = parts[1] if len(parts) > 1 else '0'
    current_time = datetime.now().strftime("%H:%M:%S")

    today_date = date.today()
    date_code = date_to_str(today_date)
    attendance_file = os.path.join(ATTENDANCE_DIR, f'Attendance-{date_code}.csv')
    expected_columns = ['Name', 'Roll', 'Time', 'CheckOut', 'Duration', 'Status']

    cfg = load_config()
    cutoff_time = cfg.get('cutoff_time', '09:30:00')

    if not os.path.exists(attendance_file):
        with open(attendance_file, 'w') as f:
            f.write(','.join(expected_columns) + '\n')

    df = pd.read_csv(attendance_file)
    for col in expected_columns:
        if col not in df.columns:
            df[col] = '-'

    df['Roll'] = df['Roll'].astype(str).str.strip()
    target_roll = str(userid).strip()

    if target_roll not in df['Roll'].values:
        # First scan today: Check-In!
        status = "On Time" if current_time <= cutoff_time else "Late"
        new_row = pd.DataFrame([{
            'Name': username,
            'Roll': target_roll,
            'Time': current_time,
            'CheckOut': '-',
            'Duration': '-',
            'Status': status
        }])
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(attendance_file, index=False)
        return 'checkin', username, current_time, status
    else:
        # User already exists in today's attendance: check if they need Check-Out
        idx = df.index[df['Roll'] == target_roll].tolist()[0]
        current_checkout = str(df.at[idx, 'CheckOut']).strip()

        if current_checkout in ['-', '', 'nan', 'None']:
            # Second scan: Check-Out!
            checkin_time = str(df.at[idx, 'Time']).strip()
            duration = calculate_duration(checkin_time, current_time)
            df.at[idx, 'CheckOut'] = current_time
            df.at[idx, 'Duration'] = duration
            df.to_csv(attendance_file, index=False)
            return 'checkout', username, current_time, duration
        else:
            # Already completed both Check-In and Check-Out today
            return 'already_done', username, str(df.at[idx, 'Time']), current_checkout

def getallusers():
    if not os.path.isdir(FACES_DIR):
        return [], [], [], 0
    raw_userlist = [u for u in os.listdir(FACES_DIR) if os.path.isdir(os.path.join(FACES_DIR, u))]
    userlist = []
    names = []
    rolls = []

    for i in raw_userlist:
        if '_' in i:
            name, roll = i.rsplit('_', 1)
            userlist.append(i)
            names.append(name)
            rolls.append(roll)
        else:
            userlist.append(i)
            names.append(i)
            rolls.append('N/A')

    return userlist, names, rolls, len(userlist)

def get_absent_users(present_rolls):
    """Returns list of registered users who have not marked attendance."""
    userlist, names, rolls, total_registered = getallusers()
    present_set = {str(r).strip() for r in present_rolls}
    absent = []
    for i in range(total_registered):
        roll_str = str(rolls[i]).strip()
        if roll_str not in present_set:
            absent.append({
                'name': names[i],
                'roll': rolls[i],
                'user_dir': userlist[i]
            })
    return absent

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Unified login for Administrators and Students/Users."""
    if session.get('logged_in'):
        if session.get('role') == 'user':
            return redirect(url_for('my_attendance'))
        return redirect(url_for('home'))
        
    if request.method == 'POST':
        login_type = request.form.get('login_type', 'admin').strip()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if login_type == 'admin':
            if check_admin_credentials(username, password):
                session['logged_in'] = True
                session['role'] = 'admin'
                session['admin_user'] = username
                flash(f'Welcome back, {username}! Successfully signed in as Administrator.', 'success')
                next_url = request.args.get('next')
                if next_url and next_url.startswith('/'):
                    return redirect(next_url)
                return redirect(url_for('home'))
            else:
                flash('Invalid Administrator username or password.', 'error')
        else:
            # Student / User Login
            success, user_name = check_user_credentials(username, password)
            if success:
                session['logged_in'] = True
                session['role'] = 'user'
                session['user_id'] = str(username).strip()
                session['user_name'] = user_name
                flash(f'Welcome, {user_name}! Successfully signed in.', 'success')
                next_url = request.args.get('next')
                if next_url and next_url.startswith('/'):
                    return redirect(next_url)
                return redirect(url_for('my_attendance'))
            else:
                flash(f'Invalid User ID or password. Ensure User ID "{username}" is registered.', 'error')
            
    cfg = load_config()
    return render_template(
        'login.html',
        org_name=cfg.get('org_name', 'FaceAttend Pro'),
        datetoday2=get_datetoday2()
    )

@app.route('/logout')
def logout():
    """Administrator & Student Logout Route."""
    session.pop('logged_in', None)
    session.pop('role', None)
    session.pop('admin_user', None)
    session.pop('user_id', None)
    session.pop('user_name', None)
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('home'))

@app.route('/my_attendance')
@login_required
def my_attendance():
    """Direct route for logged-in students to view their personal attendance."""
    if session.get('role') == 'admin':
        return redirect(url_for('home'))
    user_roll = session.get('user_id')
    return redirect(url_for('user_profile', roll=user_roll))

@app.route('/change_user_password', methods=['POST'])
@login_required
def change_user_password():
    """Allows students to update their password."""
    if session.get('role') != 'user':
        flash('Password change route for users only.', 'error')
        return redirect(url_for('home'))
        
    user_id = session.get('user_id')
    new_password = request.form.get('new_password', '').strip()
    if not new_password:
        flash('New password cannot be empty.', 'error')
        return redirect(url_for('my_attendance'))
        
    auth_data = load_user_auth()
    auth_data[str(user_id)] = {
        'password': generate_password_hash(new_password),
        'name': session.get('user_name', '')
    }
    save_user_auth(auth_data)
    flash('Your password has been updated successfully!', 'success')
    return redirect(url_for('my_attendance'))

@app.route('/')
def home():
    date_query = request.args.get('date', '').strip()
    selected_date = parse_date_query(date_query) if date_query else date.today()
    is_today = (selected_date == date.today())
    
    cfg = load_config()
    cutoff_time = cfg.get('cutoff_time', '09:30:00')
    org_name = cfg.get('org_name', 'FaceAttend Pro')

    names, rolls, times, checkouts, durations, statuses, l = extract_attendance(selected_date)
    total_registered = totalreg()
    absent_list = get_absent_users(rolls)
    absent_count = len(absent_list)
    
    on_time_count = sum(1 for s in statuses if s == 'On Time')
    late_count = sum(1 for s in statuses if s == 'Late')
    
    return render_template(
        'home.html',
        names=names,
        rolls=rolls,
        times=times,
        checkouts=checkouts,
        durations=durations,
        statuses=statuses,
        l=l,
        totalreg=total_registered,
        absent_list=absent_list,
        absent_count=absent_count,
        on_time_count=on_time_count,
        late_count=late_count,
        datetoday2=format_date_for_display(selected_date),
        selected_date_iso=selected_date.strftime("%Y-%m-%d"),
        today_iso=date.today().strftime("%Y-%m-%d"),
        is_today=is_today,
        cutoff_time=cutoff_time,
        org_name=org_name,
        is_logged_in=session.get('logged_in', False),
        user_role=session.get('role'),
        admin_user=session.get('admin_user', 'Admin'),
        user_name=session.get('user_name', '')
    )

@app.route('/settings', methods=['POST'])
@admin_required
def update_settings():
    """Update system settings (Admin Only)."""
    org_name = request.form.get('org_name', '').strip() or 'FaceAttend Pro'
    cutoff_time = request.form.get('cutoff_time', '').strip() or '09:30:00'
    new_password = request.form.get('new_password', '').strip()
    
    cfg = load_config()
    cfg['org_name'] = org_name
    cfg['cutoff_time'] = cutoff_time
    if new_password:
        cfg['admin_password'] = generate_password_hash(new_password)
        flash('Settings and admin password updated successfully!', 'success')
    else:
        flash('Settings updated successfully!', 'success')
        
    save_config(cfg)
    return redirect(request.referrer or url_for('home'))

@app.route('/mark_manual', methods=['POST'])
@admin_required
def mark_manual():
    """Allows manual override to mark an absent student Present or On Leave (Admin Only)."""
    target_roll = request.form.get('roll', '').strip()
    status_choice = request.form.get('status', 'Present (Manual)').strip()
    target_date_str = request.form.get('date', '').strip()
    
    target_date = parse_date_query(target_date_str) if target_date_str else date.today()
    date_code = date_to_str(target_date)
    attendance_file = os.path.join(ATTENDANCE_DIR, f'Attendance-{date_code}.csv')
    expected_columns = ['Name', 'Roll', 'Time', 'CheckOut', 'Duration', 'Status']

    userlist, names, rolls, total_registered = getallusers()
    student_name = "Student"
    for i in range(total_registered):
        if str(rolls[i]).strip() == target_roll:
            student_name = names[i]
            break

    if not os.path.exists(attendance_file):
        with open(attendance_file, 'w') as f:
            f.write(','.join(expected_columns) + '\n')

    df = pd.read_csv(attendance_file)
    for col in expected_columns:
        if col not in df.columns:
            df[col] = '-'

    df['Roll'] = df['Roll'].astype(str).str.strip()
    current_time = datetime.now().strftime("%H:%M:%S")

    if target_roll in df['Roll'].values:
        flash(f'{student_name} is already recorded for {format_date_for_display(target_date)}.', 'info')
    else:
        new_row = pd.DataFrame([{
            'Name': student_name,
            'Roll': target_roll,
            'Time': current_time if 'Leave' not in status_choice else '-',
            'CheckOut': '-',
            'Duration': '-',
            'Status': status_choice
        }])
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(attendance_file, index=False)
        flash(f'Manual attendance recorded for {student_name} ({status_choice})!', 'success')

    return redirect(request.referrer or url_for('home', date=target_date.strftime("%Y-%m-%d")))

@app.route('/reset_attendance', methods=['POST'])
@admin_required
def reset_attendance():
    """Resets attendance records for the selected date (Admin Only)."""
    target_date_str = request.form.get('date', '').strip()
    target_date = parse_date_query(target_date_str) if target_date_str else date.today()
    date_code = date_to_str(target_date)
    attendance_file = os.path.join(ATTENDANCE_DIR, f'Attendance-{date_code}.csv')
    expected_columns = ['Name', 'Roll', 'Time', 'CheckOut', 'Duration', 'Status']
    
    try:
        with open(attendance_file, 'w') as f:
            f.write(','.join(expected_columns) + '\n')
        flash(f'Attendance records for {format_date_for_display(target_date)} have been reset.', 'info')
    except Exception as e:
        flash(f'Error resetting records: {str(e)}', 'error')

    return redirect(url_for('home', date=target_date.strftime("%Y-%m-%d")))

@app.route('/user_profile/<roll>')
@login_required
def user_profile(roll):
    """
    Displays detailed attendance history and statistics for a single student.
    Admins can view any student; Students can only view their own profile.
    """
    target_roll = str(roll).strip()
    
    if session.get('role') == 'user':
        logged_in_roll = str(session.get('user_id', '')).strip()
        if logged_in_roll != target_roll:
            flash('Access restricted. You can only view your own attendance profile.', 'warning')
            return redirect(url_for('user_profile', roll=logged_in_roll))

    userlist, names, rolls, total_registered = getallusers()
    user_name = "User"
    user_folder = ""
    found = False
    for i in range(total_registered):
        if str(rolls[i]).strip() == target_roll:
            user_name = names[i]
            user_folder = userlist[i]
            found = True
            break
            
    if not found:
        flash(f'User with ID {roll} not found.', 'error')
        return redirect(url_for('home'))

    cfg = load_config()
    history_records = []
    days_present = 0
    days_absent = 0
    days_leave = 0

    if os.path.isdir(ATTENDANCE_DIR):
        csv_files = [f for f in os.listdir(ATTENDANCE_DIR) if f.startswith('Attendance-') and f.endswith('.csv')]
        
        def get_file_date(fname):
            try:
                date_part = fname.replace('Attendance-', '').replace('.csv', '')
                return datetime.strptime(date_part, "%m_%d_%y").date()
            except Exception:
                return date.min
                
        csv_files.sort(key=get_file_date, reverse=True)

        for fname in csv_files:
            file_date = get_file_date(fname)
            if file_date == date.min:
                continue
            fpath = os.path.join(ATTENDANCE_DIR, fname)
            try:
                df = pd.read_csv(fpath)
                if 'Roll' not in df.columns:
                    continue
                df['Roll'] = df['Roll'].astype(str).str.strip()
                matches = df[df['Roll'] == target_roll]
                if len(matches) > 0:
                    row = matches.iloc[0]
                    st = str(row.get('Status', 'On Time')).strip()
                    cin = str(row.get('Time', '-')).strip()
                    cout = str(row.get('CheckOut', '-')).strip()
                    dur = str(row.get('Duration', '-')).strip()
                    if 'Leave' in st:
                        days_leave += 1
                    else:
                        days_present += 1
                    history_records.append({
                        'date_display': format_date_for_display(file_date),
                        'check_in': cin,
                        'check_out': cout,
                        'duration': dur,
                        'status': st
                    })
                else:
                    days_absent += 1
                    history_records.append({
                        'date_display': format_date_for_display(file_date),
                        'check_in': '-',
                        'check_out': '-',
                        'duration': '-',
                        'status': 'Absent'
                    })
            except Exception:
                pass

    total_sessions = len(history_records)
    attendance_pct = (days_present / total_sessions * 100) if total_sessions > 0 else 0

    return render_template(
        'user_profile.html',
        user_name=user_name,
        user_roll=target_roll,
        user_folder=user_folder,
        total_sessions=total_sessions,
        days_present=days_present,
        days_absent=days_absent,
        days_leave=days_leave,
        attendance_pct=attendance_pct,
        history_records=history_records,
        org_name=cfg.get('org_name', 'FaceAttend Pro'),
        user_role=session.get('role', 'user')
    )

@app.route('/download')
@app.route('/download/<date_str>')
def download_csv(date_str=None):
    """Download attendance CSV for today or selected date."""
    if not date_str:
        date_str = request.args.get('date', '').strip()
    target_date = parse_date_query(date_str) if date_str else date.today()
    date_code = date_to_str(target_date)
    attendance_file = os.path.join(ATTENDANCE_DIR, f'Attendance-{date_code}.csv')
    
    expected_columns = ['Name', 'Roll', 'Time', 'CheckOut', 'Duration', 'Status']
    if not os.path.exists(attendance_file):
        with open(attendance_file, 'w') as f:
            f.write(','.join(expected_columns) + '\n')
            
    return send_file(
        attendance_file,
        as_attachment=True,
        download_name=f'Attendance-{target_date.strftime("%Y-%m-%d")}.csv',
        mimetype='text/csv'
    )

@app.route('/api/stats')
def get_stats():
    """API endpoint to get attendance statistics"""
    date_query = request.args.get('date', '').strip()
    selected_date = parse_date_query(date_query) if date_query else date.today()
    names, rolls, times, checkouts, durations, statuses, l = extract_attendance(selected_date)
    total_registered = totalreg()
    absent_count = max(0, total_registered - l)
    attendance_rate = (l / total_registered * 100) if total_registered > 0 else 0
    
    cfg = load_config()
    cutoff_time = cfg.get('cutoff_time', '09:30:00')
    on_time_count = sum(1 for s in statuses if s == 'On Time')
    late_count = sum(1 for s in statuses if s == 'Late')
    
    return jsonify({
        'present_today': l,
        'absent_today': absent_count,
        'total_registered': total_registered,
        'attendance_rate': round(attendance_rate, 1),
        'on_time_count': on_time_count,
        'late_count': late_count,
        'cutoff_time': cutoff_time,
        'date': format_date_for_display(selected_date),
        'date_iso': selected_date.strftime("%Y-%m-%d")
    })

@app.route('/users')
@admin_required
def list_users():
    """Display all registered users (Admin Only)"""
    userlist, names, rolls, l = getallusers()
    cfg = load_config()
    return render_template(
        'users.html',
        userlist=userlist,
        names=names,
        rolls=rolls,
        l=l,
        datetoday2=get_datetoday2(),
        org_name=cfg.get('org_name', 'FaceAttend Pro'),
        cutoff_time=cfg.get('cutoff_time', '09:30:00')
    )

@app.route('/delete_user/<username>')
@admin_required
def delete_user(username):
    """Delete a user from the system (Admin Only)"""
    try:
        user_folder = os.path.join(FACES_DIR, username)
        if os.path.exists(user_folder):
            import shutil
            shutil.rmtree(user_folder)
            # Retrain model after deletion or clean up if none remain
            if totalreg() > 0:
                train_model()
            else:
                model_file = os.path.join(STATIC_DIR, 'face_recognition_model.pkl')
                if os.path.exists(model_file):
                    os.remove(model_file)
            flash(f'User {username} has been successfully deleted!', 'success')
        else:
            flash(f'User {username} not found!', 'error')
    except Exception as e:
        flash(f'Error deleting user: {str(e)}', 'error')
    
    return redirect(url_for('list_users'))

@app.route('/start', methods=['GET'])
def start():
    if 'face_recognition_model.pkl' not in os.listdir(STATIC_DIR):
        flash('There is no trained model in the static folder. Please add a new face to continue.', 'error')
        return redirect(url_for('home'))

    attendance_taken = False
    action_result = None
    last_identified_person = None

    try:
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            flash('Could not access camera. Please check camera permissions.', 'error')
            return redirect(url_for('home'))
        
        # Variables to control attendance capture
        face_detected_frames = 0
        required_frames = 30  # Number of consecutive frames to confirm face detection
        max_frames = 300  # Maximum frames to prevent infinite loop (10 seconds at 30fps)
        frame_count = 0
        
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
                    action_result = add_attendance(identified_person)
                    attendance_taken = True
                    res_type, res_user, res_time, res_extra = action_result
                    
                    if res_type == 'checkin':
                        cv2.putText(frame, 'CHECK-IN SUCCESS!', (30, 65),
                                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
                        cv2.putText(frame, f'Welcome {res_user} ({res_extra})', (30, 100),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                    elif res_type == 'checkout':
                        cv2.putText(frame, 'CHECK-OUT SUCCESS!', (30, 65),
                                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 200, 255), 3)
                        cv2.putText(frame, f'Goodbye {res_user} - Stayed: {res_extra}', (30, 100),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 200, 255), 2)
                    else:  # already_done
                        cv2.putText(frame, 'ALREADY COMPLETED TODAY!', (30, 65),
                                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 165, 255), 3)
                        cv2.putText(frame, f'{res_user} already checked out', (30, 100),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)
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
            if key == 27 or attendance_taken:
                if attendance_taken:
                    cv2.waitKey(2000)  # Wait 2 seconds to show success message
                break
                
    except Exception as e:
        flash(f'Error during face recognition: {str(e)}', 'error')
    finally:
        cap.release()
        cv2.destroyAllWindows()
    
    if attendance_taken and action_result:
        res_type, res_user, res_time, res_extra = action_result
        if res_type == 'checkin':
            flash(f'Check-In recorded successfully for {res_user}! Status: {res_extra} at {res_time}', 'success')
        elif res_type == 'checkout':
            flash(f'Check-Out recorded successfully for {res_user}! Total Duration: {res_extra}', 'success')
        else:
            flash(f'Hi {res_user}! You have already completed Check-In and Check-Out today.', 'info')
    else:
        flash('No face detected or attendance recording timed out. Please try again.', 'warning')
    
    return redirect(url_for('home'))

@app.route('/add', methods=['GET', 'POST'])
@admin_required
def add():
    """Register new user with face images (Admin Only)."""
    if request.method == 'GET':
        return render_template('add_user.html', datetoday2=get_datetoday2())
    
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
