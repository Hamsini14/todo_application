import json
import os
from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime

app = Flask(__name__)
TASKS_FILE = 'tasks.json'

def load_tasks():
    if not os.path.exists(TASKS_FILE):
        return []
    with open(TASKS_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_tasks(tasks):
    with open(TASKS_FILE, 'w') as f:
        json.dump(tasks, f, indent=4)

@app.route('/')
def index():
    tasks = load_tasks()
    return render_template('index.html', tasks=tasks)

@app.route('/add', methods=['POST'])
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
            'day': day_name
        }
        tasks.append(new_task)
        save_tasks(tasks)
    return redirect(url_for('index'))

@app.route('/edit/<int:task_id>', methods=['POST'])
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
def delete_task(task_id):
    tasks = load_tasks()
    tasks = [task for task in tasks if task['id'] != task_id]
    save_tasks(tasks)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
