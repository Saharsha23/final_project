import unittest
from app import app, db, User, Poll, PollOption, Vote
from werkzeug.security import generate_password_hash
import json
import pymysql
from sqlalchemy import text

class TestApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create test database
        connection = pymysql.connect(
            host='localhost',
            user='root',
            password='',
            charset='utf8mb4'
        )
        try:
            with connection.cursor() as cursor:
                cursor.execute('DROP DATABASE IF EXISTS poll_maker_test')
                cursor.execute('CREATE DATABASE poll_maker_test')
            connection.commit()
        finally:
            connection.close()

    def setUp(self):
        # Set up test database
        app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost:3306/poll_maker_test'
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.app = app.test_client()
        
        # Create test database and tables
        with app.app_context():
            # Drop all tables first to ensure clean state
            db.session.execute(text("DROP TABLE IF EXISTS vote"))
            db.session.execute(text("DROP TABLE IF EXISTS poll_option"))
            db.session.execute(text("DROP TABLE IF EXISTS poll"))
            db.session.execute(text("DROP TABLE IF EXISTS user"))
            db.session.commit()

            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS user (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(80) UNIQUE NOT NULL,
                    email VARCHAR(120) UNIQUE NOT NULL,
                    password_hash VARCHAR(512) NOT NULL
                )
            """))
            
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS poll (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    title VARCHAR(200) NOT NULL,
                    description TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    user_id INT NOT NULL,
                    is_private BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (user_id) REFERENCES user(id)
                )
            """))
            
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS poll_option (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    text VARCHAR(200) NOT NULL,
                    poll_id INT NOT NULL,
                    FOREIGN KEY (poll_id) REFERENCES poll(id) ON DELETE CASCADE
                )
            """))
            
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS vote (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    poll_id INT NOT NULL,
                    option_id INT NOT NULL,
                    voted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES user(id),
                    FOREIGN KEY (poll_id) REFERENCES poll(id),
                    FOREIGN KEY (option_id) REFERENCES poll_option(id)
                )
            """))
            
            db.session.commit()
            
            # Create test user
            test_user = User(
                username='testuser',
                email='test@example.com',
                password_hash=generate_password_hash('testpass123')
            )
            db.session.add(test_user)
            db.session.commit()
            
            # Create test poll
            test_poll = Poll(
                title='Test Poll Question',
                description='This is a test poll description',
                user_id=test_user.id
            )
            db.session.add(test_poll)
            db.session.commit()
            
            # Create test options
            option1 = PollOption(text='Option 1', poll_id=test_poll.id)
            option2 = PollOption(text='Option 2', poll_id=test_poll.id)
            db.session.add_all([option1, option2])
            db.session.commit()

    def tearDown(self):
        with app.app_context():
            db.session.execute(text('SET FOREIGN_KEY_CHECKS = 0'))
            db.session.execute(text('DROP TABLE IF EXISTS vote'))
            db.session.execute(text('DROP TABLE IF EXISTS poll_option'))
            db.session.execute(text('DROP TABLE IF EXISTS poll'))
            db.session.execute(text('DROP TABLE IF EXISTS user'))
            db.session.execute(text('SET FOREIGN_KEY_CHECKS = 1'))
            db.session.commit()

    @classmethod
    def tearDownClass(cls):
        # Drop test database
        connection = pymysql.connect(
            host='localhost',
            user='root',
            password='',
            charset='utf8mb4'
        )
        try:
            with connection.cursor() as cursor:
                cursor.execute('DROP DATABASE IF EXISTS poll_maker_test')
            connection.commit()
        finally:
            connection.close()

    def test_landing_page(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Create & Share Polls Instantly', response.data)

    def test_register(self):
        # Test registration with missing fields
        response = self.app.post('/register', data={
            'username': '',
            'email': '',
            'password': ''
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Please enter both username and password', response.data)
        
        # Test successful registration
        response = self.app.post('/register', data={
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        
        # Verify user was created
        with app.app_context():
            user = User.query.filter_by(username='newuser').first()
            self.assertIsNotNone(user)
            self.assertEqual(user.email, 'new@example.com')

    def test_login(self):
        # Login first
        response = self.app.post('/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Your Polls', response.data)  # Check for dashboard content

    def test_create_poll(self):
        # Login first
        self.app.post('/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        # Create poll
        response = self.app.post('/create', data={
            'title': 'New Test Poll',
            'description': 'This is a new test poll',
            'options': ['Option 1', 'Option 2', 'Option 3']
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Poll created successfully!', response.data)

    def test_vote(self):
        # Login first
        self.app.post('/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        # Get the test poll
        with app.app_context():
            poll = Poll.query.first()
            option = PollOption.query.first()
            
        # Vote on the poll
        response = self.app.post(f'/vote/{poll.id}', data={
            'option': option.id
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Vote Recorded Successfully!', response.data)

    def test_view_poll(self):
        # Login first
        self.app.post('/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        with app.app_context():
            poll = Poll.query.first()
            
        response = self.app.get(f'/poll/{poll.id}')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Test Poll Question', response.data)

    def test_delete_poll(self):
        # Login first
        response = self.app.post('/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        }, follow_redirects=True)
        
        # Get the first poll
        with app.app_context():
            poll = Poll.query.first()
            
        # Try to delete the poll
        response = self.app.post(f'/poll/{poll.id}/delete', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        
        # Verify the poll was deleted
        with app.app_context():
            deleted_poll = Poll.query.get(poll.id)
            self.assertIsNone(deleted_poll)

    def test_logout(self):
        # Login first
        self.app.post('/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        response = self.app.get('/logout', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Create & Share Polls Instantly', response.data)  # Check for landing page content

    def test_invalid_login(self):
        response = self.app.post('/login', data={
            'username': 'wronguser',
            'password': 'wrongpass'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Username not found', response.data)

    def test_duplicate_username(self):
        response = self.app.post('/register', data={
            'username': 'testuser',  # Already exists
            'email': 'another@example.com',
            'password': 'newpass123'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Username already exists', response.data)

if __name__ == '__main__':
    unittest.main() 