import pytest
from app import app, db, User, Poll, PollOption, Vote
from werkzeug.security import generate_password_hash

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.session.remove()
            db.drop_all()

@pytest.fixture
def test_user():
    user = User(
        username='testuser',
        email='test@example.com',
        password_hash=generate_password_hash('password123')
    )
    db.session.add(user)
    db.session.commit()
    return user

def test_index_page(client):
    response = client.get('/')
    assert response.status_code == 200

def test_register_page(client):
    response = client.get('/register')
    assert response.status_code == 200

def test_login_page(client):
    response = client.get('/login')
    assert response.status_code == 200

def test_register_user(client):
    response = client.post('/register', data={
        'username': 'newuser',
        'email': 'new@example.com',
        'password': 'password123'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Registration successful' in response.data

def test_login_user(client, test_user):
    response = client.post('/login', data={
        'username': 'testuser',
        'password': 'password123'
    }, follow_redirects=True)
    assert response.status_code == 200

def test_create_poll(client, test_user):
    # Login first
    client.post('/login', data={
        'username': 'testuser',
        'password': 'password123'
    })
    
    # Create poll
    response = client.post('/create', data={
        'title': 'Test Poll',
        'description': 'Test Description',
        'options': ['Option 1', 'Option 2']
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Poll created successfully' in response.data

def test_view_poll(client, test_user):
    # Login first
    client.post('/login', data={
        'username': 'testuser',
        'password': 'password123'
    })
    
    # Create a poll
    poll = Poll(
        title='Test Poll',
        description='Test Description',
        user_id=test_user.id
    )
    db.session.add(poll)
    db.session.commit()
    
    option1 = PollOption(text='Option 1', poll_id=poll.id)
    option2 = PollOption(text='Option 2', poll_id=poll.id)
    db.session.add(option1)
    db.session.add(option2)
    db.session.commit()
    
    # View the poll
    response = client.get(f'/poll/{poll.id}')
    assert response.status_code == 200
    assert b'Test Poll' in response.data

def test_vote_on_poll(client, test_user):
    # Login first
    client.post('/login', data={
        'username': 'testuser',
        'password': 'password123'
    })
    
    # Create a poll
    poll = Poll(
        title='Test Poll',
        description='Test Description',
        user_id=test_user.id
    )
    db.session.add(poll)
    db.session.commit()
    
    option1 = PollOption(text='Option 1', poll_id=poll.id)
    option2 = PollOption(text='Option 2', poll_id=poll.id)
    db.session.add(option1)
    db.session.add(option2)
    db.session.commit()
    
    # Vote on the poll
    response = client.post(f'/vote/{poll.id}', data={
        'option': option1.id
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Your vote has been recorded' in response.data

def test_delete_poll(client, test_user):
    # Login first
    client.post('/login', data={
        'username': 'testuser',
        'password': 'password123'
    })
    
    # Create a poll
    poll = Poll(
        title='Test Poll',
        description='Test Description',
        user_id=test_user.id
    )
    db.session.add(poll)
    db.session.commit()
    
    # Delete the poll
    response = client.post(f'/poll/{poll.id}/delete', follow_redirects=True)
    assert response.status_code == 200
    assert b'Poll deleted successfully' in response.data 