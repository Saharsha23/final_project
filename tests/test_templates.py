import pytest
from bs4 import BeautifulSoup
from app import app, db, User, Poll, PollOption
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

def test_landing_page_structure(client):
    """Test the structure of the landing page"""
    response = client.get('/')
    assert response.status_code == 200
    
    soup = BeautifulSoup(response.data, 'html.parser')
    
    # Check main heading
    assert soup.find('h1', string='Create & Share Polls Instantly') is not None
    
    # Check for registration and login links
    nav = soup.find('nav')
    assert nav is not None
    assert nav.find('a', string='Register') is not None
    assert nav.find('a', string='Login') is not None

def test_login_page_structure(client):
    """Test the structure of the login page"""
    response = client.get('/login')
    assert response.status_code == 200
    
    soup = BeautifulSoup(response.data, 'html.parser')
    
    # Check form elements
    form = soup.find('form', {'method': 'POST'})
    assert form is not None
    
    # Check input fields
    assert soup.find('input', {'name': 'username'}) is not None
    assert soup.find('input', {'name': 'password'}) is not None
    assert soup.find('button', {'type': 'submit'}) is not None

def test_create_poll_page_structure(client, test_user):
    """Test the structure of the create poll page"""
    # Login first
    client.post('/login', data={
        'username': 'testuser',
        'password': 'password123'
    })
    
    response = client.get('/create')
    assert response.status_code == 200
    
    soup = BeautifulSoup(response.data, 'html.parser')
    
    # Check form elements
    form = soup.find('form', {'method': 'POST'})
    assert form is not None
    
    # Check input fields
    assert soup.find('input', {'name': 'title'}) is not None
    assert soup.find('textarea', {'name': 'description'}) is not None
    assert soup.find('button', {'type': 'submit'}) is not None

def test_view_poll_page_structure(client, test_user):
    """Test the structure of the view poll page"""
    # Login and create a poll
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
    
    # Test basic poll view
    response = client.get(f'/poll/{poll.id}')
    assert response.status_code == 200
    
    soup = BeautifulSoup(response.data, 'html.parser')
    
    # Check poll content
    assert soup.find(string='Test Poll') is not None
    assert soup.find(string='Test Description') is not None
    
    # Check voting form
    form = soup.find('form', {'method': 'POST'})
    assert form is not None
    assert form.get('action') == f'/vote/{poll.id}'
    
    # Check options
    options = soup.find_all('input', {'type': 'radio', 'name': 'option'})
    assert len(options) == 2
    
    # Check share link (should be present for poll owner)
    share_link = soup.find('input', {'id': 'shareLink'})
    assert share_link is not None
    assert share_link.get('value') == f'http://localhost/poll/{poll.id}'
    
    # Check admin view elements
    assert soup.find('canvas', {'id': 'resultsChart'}) is not None
    chart_buttons = soup.find_all('button', {'data-chart-type': True})
    assert len(chart_buttons) == 4  # pie, bar, doughnut, line

def test_my_polls_page_structure(client, test_user):
    """Test the structure of the my polls page"""
    # Login first
    client.post('/login', data={
        'username': 'testuser',
        'password': 'password123'
    })
    
    response = client.get('/my_polls')
    assert response.status_code == 200
    
    soup = BeautifulSoup(response.data, 'html.parser')
    
    # Check sections
    assert soup.find('h3', string='My Created Polls') is not None
    assert soup.find('h3', string='Polls I Voted On') is not None
    
    # Check create poll button
    create_btn = soup.find('a', string='Create New Poll')
    assert create_btn is not None
    assert create_btn.get('href') == '/create'

def test_flash_messages_rendering(client):
    """Test if flash messages are properly rendered"""
    # First request to initialize the session
    client.get('/')
    
    # Set flash message
    with client.session_transaction() as session:
        session['_flashes'] = [('info', 'Test message')]
    
    # Second request to check if flash message is rendered
    response = client.get('/')
    assert response.status_code == 200
    
    soup = BeautifulSoup(response.data, 'html.parser')
    flash_message = soup.find('div', class_='alert-info')
    assert flash_message is not None, "Flash message div not found"
    assert 'Test message' in flash_message.text, "Flash message text not found"

def test_navigation_when_logged_in(client, test_user):
    """Test navigation elements when user is logged in"""
    client.post('/login', data={
        'username': 'testuser',
        'password': 'password123'
    })
    
    response = client.get('/')
    assert response.status_code == 200
    
    soup = BeautifulSoup(response.data, 'html.parser')
    nav = soup.find('nav')
    
    # Check that logged-in specific links are present
    assert soup.find('a', {'class': 'dropdown-toggle'}) is not None
    assert soup.find('a', {'class': 'dropdown-item'}, string='Logout') is not None
    
    # Check that login/register links are not present
    assert soup.find('a', {'class': 'nav-link', 'href': '/login'}) is None
    assert soup.find('a', {'class': 'nav-link', 'href': '/register'}) is None 