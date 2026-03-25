import pytest
import os
import json
from app import app, init_db, USERS_FILE, TASKS_FILE

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.secret_key = 'test-secret'
    # Use a clean users and tasks file for testing
    if os.path.exists(USERS_FILE):
        os.remove(USERS_FILE)
    if os.path.exists(TASKS_FILE):
        os.remove(TASKS_FILE)
    init_db()
    with app.test_client() as client:
        yield client
    if os.path.exists(USERS_FILE):
        os.remove(USERS_FILE)
    if os.path.exists(TASKS_FILE):
        os.remove(TASKS_FILE)

def test_signup(client):
    response = client.post('/signup', data={'username': 'testuser', 'password': 'testpassword'}, follow_redirects=True)
    assert b"Signup successful" in response.data
    with open(USERS_FILE, 'r') as f:
        users = json.load(f)
        assert any(u['username'] == 'testuser' for u in users)

def test_login_success(client):
    client.post('/signup', data={'username': 'testuser', 'password': 'testpassword'})
    response = client.post('/login', data={'username': 'testuser', 'password': 'testpassword'}, follow_redirects=True)
    assert b"Your Schedule" in response.data

def test_login_fail(client):
    response = client.post('/login', data={'username': 'wronguser', 'password': 'wrongpassword'}, follow_redirects=True)
    assert b"Invalid credentials" in response.data

def test_protected_route(client):
    response = client.get('/', follow_redirects=True)
    assert b"Login to TaskNest" in response.data

def test_task_completion(client):
    # Signup and Login
    client.post('/signup', data={'username': 'testuser', 'password': 'testpassword'})
    client.post('/login', data={'username': 'testuser', 'password': 'testpassword'})
    
    # Add a task
    client.post('/add', data={'task': 'Test Task', 'date': '2099-01-01'})
    
    # Check if task appears in view
    response = client.get('/')
    assert b"Test Task" in response.data
    
    # Complete task
    with open(TASKS_FILE, 'r') as f:
        tasks = json.load(f)
        task_id = tasks[0]['id']
    
    client.post(f'/complete/{task_id}', follow_redirects=True)
    
    # Check if task is removed from view
    response = client.get('/')
    assert b"Test Task" not in response.data
    
    # Verify in JSON that it is completed
    with open(TASKS_FILE, 'r') as f:
        tasks = json.load(f)
        assert tasks[0]['completed'] == True
