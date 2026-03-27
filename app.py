import json
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from functools import wraps

# ---------------- ENV LOADING ----------------
def load_env():
    found = os.path.exists('.env')
    if found:
        with open('.env') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip().strip("'").strip('"')
    
    # Render/Production Log: Check if variables exist in environment
    print(f"[{datetime.now()}] Environment Check: SMTP_EMAIL set? {'Yes' if 'SMTP_EMAIL' in os.environ else 'No'}")
    print(f"[{datetime.now()}] Environment Check: SMTP_PASSWORD set? {'Yes' if 'SMTP_PASSWORD' in os.environ else 'No'}")
    
    return found

ENV_FOUND = load_env()

app = Flask(__name__)
app.secret_key = 'super-secret-key-change-this-in-production'

TASKS_FILE = 'tasks.json'
USERS_FILE = 'users.json'
LOG_FILE = 'email_errors.log'

# ---------------- INIT ----------------
def init_db():
    if not os.path.exists(TASKS_FILE):
        with open(TASKS_FILE, 'w') as f:
            json.dump([], f)
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w') as f:
            json.dump([], f)

# ---------------- USERS ----------------
def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, 'r') as f:
        try:
            return json.load(f)
        except:
            return []

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

# ---------------- TASKS ----------------
def load_tasks():
    if not os.path.exists(TASKS_FILE):
        return []
    with open(TASKS_FILE, 'r') as f:
        try:
            return json.load(f)
        except:
            return []

def save_tasks(tasks):
    with open(TASKS_FILE, 'w') as f:
        json.dump(tasks, f, indent=4)

# ---------------- LOGIN REQUIRED ----------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ---------------- AUTH ----------------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        users = load_users()

        if any(user['username'] == username for user in users):
            flash("User already exists!")
            return render_template('signup.html')

        email = request.form.get('email')
        users.append({'username': username, 'password': password, 'email': email})
        save_users(users)

        flash("Signup successful! Please login.")
        return redirect(url_for('login'))

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        users = load_users()
        user = next((u for u in users if u['username'] == username and u['password'] == password), None)

        if user:
            session['username'] = username
            session['email'] = user.get('email')
            return redirect(url_for('index'))
        else:
            flash("Invalid credentials!")

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('email', None)
    return redirect(url_for('login'))


# ---------------- EMAIL UTILITY ----------------
def send_deadline_email(receiver_email, task_content, deadline):
    # SMTP Configuration (Using placeholders - User should set these)
    sender_email = os.environ.get('SMTP_EMAIL', 'your-gmail@gmail.com')
    sender_password = os.environ.get('SMTP_PASSWORD', 'your-app-password')

    # Debug Log: Track sending attempts
    debug_msg = f"[{datetime.now()}] Info: Attempting email to {receiver_email} from {sender_email}\n"
    with open(LOG_FILE, 'a') as f:
        f.write(debug_msg)
    print(debug_msg.strip()) # Visible in Render Dashboard
    
    smtp_server = "smtp.gmail.com"
    smtp_port = 587

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = f"Deadline Alert: {task_content}"

    body = f"Hello,\n\nThis is a reminder that your task '{task_content}' is due on {deadline}.\n\nPlease complete it soon!\n\nBest,\nTaskNest Team"
    message.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, message.as_string())
        server.quit()
        return True
    except Exception as e:
        error_msg = f"[{datetime.now()}] Error sending to {receiver_email}: {str(e)}\n"
        with open(LOG_FILE, 'a') as f:
            f.write(error_msg)
        print(error_msg)
        return False

# ---------------- MAIN ----------------
@app.route('/')
@login_required
def index():
    tasks = load_tasks()
    today = datetime.now().date()
    updated = False

    # 🔥 FILTER USER TASKS & CHECK NOTIFICATIONS
    user_tasks = []
    for t in tasks:
        if t.get('user') == session['username'] and not t.get('completed', False):
            # Safe priority & notified handling
            if 'priority' not in t: t['priority'] = 'Medium'
            if 'notified' not in t: t['notified'] = False
            
            # Deadline Warning Logic
            t['warning'] = None
            task_date_str = t.get('date')
            if task_date_str:
                try:
                    task_date = datetime.strptime(task_date_str, '%Y-%m-%d').date()
                    diff = (task_date - today).days
                    
                    if diff == 0:
                        t['warning'] = "⚠️ Due Today"
                    elif diff == 1:
                        t['warning'] = "⏳ Tomorrow"
                    elif diff == 2:
                        t['warning'] = "📅 Due Soon"

                    # Email logic: within 2 days and not notified
                    if 0 <= diff <= 2 and not t.get('notified'):
                        if session.get('email'):
                            if send_deadline_email(session['email'], t['content'], t['date']):
                                t['notified'] = True
                                updated = True
                                flash(f"Notification email sent to {session['email']} for '{t['content']}'", "success")
                            else:
                                flash(f"Failed to send email for '{t['content']}'. Check email_errors.log", "danger")
                except Exception as e:
                    print(f"Error in deadline logic: {e}")
            
            user_tasks.append(t)

    if updated:
        save_tasks(tasks)

    return render_template('index.html', tasks=user_tasks)


@app.route('/notifications')
@login_required
def notifications():
    tasks = load_tasks()
    today = datetime.now().date()
    upcoming_tasks = []

    for t in tasks:
        if t.get('user') == session['username'] and not t.get('completed', False):
            task_date_str = t.get('date')
            if task_date_str:
                try:
                    task_date = datetime.strptime(task_date_str, '%Y-%m-%d').date()
                    diff = (task_date - today).days
                    if 0 <= diff <= 2:
                        # Add warning label for template
                        if diff == 0: t['warning'] = "Today"
                        elif diff == 1: t['warning'] = "Tomorrow"
                        else: t['warning'] = "Due Soon"
                        upcoming_tasks.append(t)
                except:
                    pass

    return render_template('notifications.html', tasks=upcoming_tasks)

# ---------------- ADD ----------------
@app.route('/add', methods=['POST'])
@login_required
def add_task():
    task_content = request.form.get('task')
    task_date = request.form.get('date')
    task_priority = request.form.get('priority', 'Medium')

    if task_content:
        # Prevent past date
        if task_date:
            try:
                date_obj = datetime.strptime(task_date, '%Y-%m-%d').date()
                if date_obj < datetime.now().date():
                    return redirect(url_for('index', error="past_date"))
            except:
                pass

        tasks = load_tasks()

        day_name = ""
        if task_date:
            try:
                date_obj = datetime.strptime(task_date, '%Y-%m-%d')
                day_name = date_obj.strftime('%A')
            except:
                pass

        new_task = {
            'id': len(tasks) + 1 if not tasks else max(t['id'] for t in tasks) + 1,
            'user': session['username'],  # 🔥 IMPORTANT
            'content': task_content,
            'date': task_date,
            'day': day_name,
            'priority': task_priority,
            'completed': False,
            'notified': False  # 🔥 NEW
        }

        tasks.append(new_task)
        save_tasks(tasks)

    return redirect(url_for('index'))

# ---------------- EDIT ----------------
@app.route('/edit/<int:task_id>', methods=['POST'])
@login_required
def edit_task(task_id):
    task_content = request.form.get('task')
    task_date = request.form.get('date')
    task_priority = request.form.get('priority')

    tasks = load_tasks()

    for task in tasks:
        if task['id'] == task_id and task.get('user') == session['username']:
            if task_content:
                task['content'] = task_content

            if task_priority:
                task['priority'] = task_priority

            if task_date:
                try:
                    date_obj = datetime.strptime(task_date, '%Y-%m-%d').date()
                    if date_obj < datetime.now().date():
                        return redirect(url_for('index', error="past_date"))

                    task['date'] = task_date
                    task['day'] = datetime.strptime(task_date, '%Y-%m-%d').strftime('%A')
                except:
                    pass
            break

    save_tasks(tasks)
    return redirect(url_for('index'))

# ---------------- DELETE ----------------
@app.route('/delete/<int:task_id>', methods=['POST'])
@login_required
def delete_task(task_id):
    tasks = load_tasks()

    tasks = [
        task for task in tasks
        if not (task['id'] == task_id and task.get('user') == session['username'])
    ]

    save_tasks(tasks)
    return redirect(url_for('index'))

# ---------------- COMPLETE ----------------
@app.route('/complete/<int:task_id>', methods=['POST'])
@login_required
def complete_task(task_id):
    tasks = load_tasks()

    for task in tasks:
        if task['id'] == task_id and task.get('user') == session['username']:
            task['completed'] = True
            break

    save_tasks(tasks)
    return redirect(url_for('index'))

# ---------------- RUN ----------------
if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)