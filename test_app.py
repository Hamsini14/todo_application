import pytest
import os
import json
from app import app, TASKS_FILE

@pytest.fixture
def client():
    app.config['TESTING'] = True
    # Ensure a clean test environment
    if os.path.exists(TASKS_FILE):
        os.remove(TASKS_FILE)
        
    with app.test_client() as client:
        yield client
        # Clean up after test
        if os.path.exists(TASKS_FILE):
            os.remove(TASKS_FILE)

def test_index_page(client):
    """Test that the index page loads."""
    response = client.get('/')
    assert response.status_code == 200
    assert b'Your Schedule' in response.data
    assert b'TaskNest' in response.data

def test_add_task_with_date(client):
    """Test adding a task with a date."""
    data = {'task': 'Test Task', 'date': '2026-03-24'}
    response = client.post('/add', data=data, follow_redirects=True)
    assert response.status_code == 200
    assert b'Test Task' in response.data
    assert b'2026-03-24' in response.data
    assert b'Tuesday' in response.data # 2026-03-24 is a Tuesday

def test_delete_task(client):
    """Test deleting a task."""
    # First add a task
    client.post('/add', data={'task': 'Task to Delete', 'date': '2026-03-24'})
    
    with open(TASKS_FILE, 'r') as f:
        tasks = json.load(f)
    task_id = tasks[0]['id']
    
    # Then delete it
    response = client.post(f'/delete/{task_id}', follow_redirects=True)
    assert response.status_code == 200
    assert b'Task to Delete' not in response.data
    
from datetime import datetime, timedelta

def test_add_past_date(client):
    """Test that adding a task with a past date fails."""
    past_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    response = client.post('/add', data={'task': 'Old Task', 'date': past_date}, follow_redirects=True)
    assert response.status_code == 200
    assert b'Old Task' not in response.data
    assert b'Error: You cannot pick a date in the past!' in response.data

def test_edit_task(client):
    """Test editing an existing task."""
    # Add a task first
    future_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    client.post('/add', data={'task': 'Original Task', 'date': future_date})
    
    with open(TASKS_FILE, 'r') as f:
        tasks = json.load(f)
    task_id = tasks[0]['id']
    
    # Edit the task
    new_date = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
    response = client.post(f'/edit/{task_id}', data={'task': 'Updated Task', 'date': new_date}, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Updated Task' in response.data
    assert new_date.encode() in response.data
    
    with open(TASKS_FILE, 'r') as f:
        tasks_after = json.load(f)
    assert tasks_after[0]['content'] == 'Updated Task'

def test_edit_past_date(client):
    """Test that editing a task with a past date fails."""
    future_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    client.post('/add', data={'task': 'Valid Task', 'date': future_date})
    
    with open(TASKS_FILE, 'r') as f:
        tasks = json.load(f)
    task_id = tasks[0]['id']
    
    past_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    response = client.post(f'/edit/{task_id}', data={'task': 'Invalid Edit', 'date': past_date}, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Error: You cannot pick a date in the past!' in response.data
