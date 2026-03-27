import json
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = 'super-secret-key-change-this-in-production'

TASKS_FILE = 'tasks.json'
USERS_FILE = 'users.json'

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

        users.append({'username': username, 'password': password})
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
            return redirect(url_for('index'))
        else:
            flash("Invalid credentials!")

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

# ---------------- MAIN ----------------
@app.route('/')
@login_required
def index():
    tasks = load_tasks()
    today = datetime.now().date()

    # 🔥 FILTER USER TASKS
    user_tasks = []
    for t in tasks:
        if t.get('user') == session['username'] and not t.get('completed', False):
            # Safe priority handling
            if 'priority' not in t:
                t['priority'] = 'Medium'
            
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
                        t['warning'] = "⏳ Due Soon"
                except:
                    pass
            
            user_tasks.append(t)

    return render_template('index.html', tasks=user_tasks)

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
            'completed': False
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