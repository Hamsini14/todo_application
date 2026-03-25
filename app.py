import json
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = 'super-secret-key-change-this-in-production'

# Requirements: File-based storage using tasks.json and users.json
TASKS_FILE = 'tasks.json'
USERS_FILE = 'users.json'

# Create files if not exist
def init_db():
    """Ensure tasks.json and users.json exist on startup."""
    if not os.path.exists(TASKS_FILE):
        with open(TASKS_FILE, 'w') as f:
            json.dump([], f)
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w') as f:
            json.dump([], f)

def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def load_tasks():
    """Load tasks from tasks.json if it exists."""
    if not os.path.exists(TASKS_FILE):
        return []
    with open(TASKS_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_tasks(tasks):
    """Update the tasks.json file whenever a task is modified."""
    with open(TASKS_FILE, 'w') as f:
        json.dump(tasks, f, indent=4)

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

@app.route('/')
@login_required
def index():
    tasks = load_tasks()
    # Only show incomplete tasks in the main view
    tasks = [t for t in tasks if not t.get('completed', False)]
    return render_template('index.html', tasks=tasks)

@app.route('/add', methods=['POST'])
@login_required
def add_task():
    task_content = request.form.get('task')
    task_date = request.form.get('date')
    
    if task_content:
        # Validation: check if date is in the past
        if task_date:
            try:
                date_obj = datetime.strptime(task_date, '%Y-%m-%d').date()
                if date_obj < datetime.now().date():
                    # In a real app we'd use flash messages, but let's just redirect for now
                    # or add a simple error handling if needed. 
                    # For this task, I'll just skip adding if date is past.
                    return redirect(url_for('index', error="past_date"))
            except ValueError:
                pass

        tasks = load_tasks()
        day_name = ""
        if task_date:
            try:
                date_obj = datetime.strptime(task_date, '%Y-%m-%d')
                day_name = date_obj.strftime('%A')
            except ValueError:
                pass
        
        new_task = {
            'id': len(tasks) + 1 if not tasks else max(t['id'] for t in tasks) + 1,
            'content': task_content,
            'date': task_date,
            'day': day_name,
            'completed': False
        }
        tasks.append(new_task)
        save_tasks(tasks)
    return redirect(url_for('index'))

@app.route('/edit/<int:task_id>', methods=['POST'])
@login_required
def edit_task(task_id):
    task_content = request.form.get('task')
    task_date = request.form.get('date')
    
    tasks = load_tasks()
    for task in tasks:
        if task['id'] == task_id:
            if task_content:
                task['content'] = task_content
            if task_date:
                # Validation for edit too
                try:
                    date_obj = datetime.strptime(task_date, '%Y-%m-%d').date()
                    if date_obj < datetime.now().date():
                        return redirect(url_for('index', error="past_date"))
                    
                    task['date'] = task_date
                    task['day'] = datetime.strptime(task_date, '%Y-%m-%d').strftime('%A')
                except ValueError:
                    pass
            break
    save_tasks(tasks)
    return redirect(url_for('index'))

@app.route('/delete/<int:task_id>', methods=['POST'])
@login_required
def delete_task(task_id):
    tasks = load_tasks()
    tasks = [task for task in tasks if task['id'] != task_id]
    save_tasks(tasks)
    return redirect(url_for('index'))

@app.route('/complete/<int:task_id>', methods=['POST'])
@login_required
def complete_task(task_id):
    tasks = load_tasks()
    for task in tasks:
        if task['id'] == task_id:
            task['completed'] = True
            break
    save_tasks(tasks)
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()  # Create tasks.json automatically if it doesn't exist
    app.run(host='0.0.0.0', port=5000, debug=True)
