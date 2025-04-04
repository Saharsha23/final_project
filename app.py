from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dotenv import load_dotenv
from datetime import datetime
import pymysql
from sqlalchemy import text

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'

# Updated database connection string with new database name
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost:3306/POLLyverse?charset=utf8mb4'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True  # Enable SQL query logging

# Initialize SQLAlchemy with the app
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Initialize database
def init_db():
    with app.app_context():
        try:
            # Create database if it doesn't exist
            connection = pymysql.connect(
                host='localhost',
                user='root',
                password='',
                charset='utf8mb4'
            )
            with connection.cursor() as cursor:
                # Drop the old database if it exists
                cursor.execute("DROP DATABASE IF EXISTS poll_maker_data")
                # Create the new database
                cursor.execute("CREATE DATABASE IF NOT EXISTS POLLyverse")
            connection.close()
            
            # Create tables if they don't exist
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
            print("Database tables created successfully!")
        except Exception as e:
            print(f"Error creating database tables: {str(e)}")
            db.session.rollback()
            raise

# Initialize database tables if they don't exist
init_db()

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(512))  # Increased to 512 to ensure it's large enough
    polls = db.relationship('Poll', backref='creator', lazy=True)
    votes = db.relationship('Vote', backref='voter', lazy=True)

class Poll(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_private = db.Column(db.Boolean, default=False)
    options = db.relationship('PollOption', backref='poll', lazy=True, cascade='all, delete-orphan')
    votes = db.relationship('Vote', backref='poll', lazy=True)

class PollOption(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(200), nullable=False)
    poll_id = db.Column(db.Integer, db.ForeignKey('poll.id'), nullable=False)
    votes = db.relationship('Vote', backref='option', lazy=True)

class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    poll_id = db.Column(db.Integer, db.ForeignKey('poll.id'), nullable=False)
    option_id = db.Column(db.Integer, db.ForeignKey('poll_option.id'), nullable=False)
    voted_at = db.Column(db.DateTime, default=db.func.current_timestamp())

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        polls = Poll.query.filter_by(user_id=current_user.id).all()
        return render_template('index.html', polls=polls)
    return render_template('landing.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            
            if not username or not password:
                flash('Please enter both username and password', 'danger')
                return redirect(url_for('register'))
            
            if User.query.filter_by(username=username).first():
                flash('Username already exists', 'danger')
                return redirect(url_for('register'))
            
            if User.query.filter_by(email=email).first():
                flash('Email already exists', 'danger')
                return redirect(url_for('register'))
            
            user = User(username=username, email=email, password_hash=generate_password_hash(password))
            db.session.add(user)
            db.session.commit()
            
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            print(f"Registration error: {str(e)}")
            flash('An error occurred during registration. Please try again.', 'danger')
            return redirect(url_for('register'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Please enter both username and password', 'danger')
            return redirect(url_for('login'))
            
        user = User.query.filter_by(username=username).first()
        
        if not user:
            flash('Username not found', 'danger')
            return redirect(url_for('login'))
            
        if check_password_hash(user.password_hash, password):
            login_user(user)
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):  # Ensure the next URL is relative
                return redirect(next_page)
            return redirect(url_for('index'))
        else:
            flash('Invalid password', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/create', methods=['GET', 'POST'])
@login_required
def create_poll():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        options = request.form.getlist('options')
        is_private = 'is_private' in request.form
        
        if len(options) < 2:
            flash('A poll must have at least 2 options.', 'error')
            return redirect(url_for('create_poll'))
        
        poll = Poll(
            title=title, 
            description=description, 
            user_id=current_user.id,
            is_private=is_private
        )
        db.session.add(poll)
        db.session.commit()
        
        for option_text in options:
            option = PollOption(text=option_text, poll_id=poll.id)
            db.session.add(option)
        
        db.session.commit()
        flash('Poll created successfully!', 'success')
        return redirect(url_for('index'))
    
    return render_template('create_poll.html')

@app.route('/poll/<int:poll_id>')
def view_poll(poll_id):
    poll = Poll.query.get_or_404(poll_id)
    
    # If poll is private and user is not the creator, show error
    if poll.is_private and current_user.is_authenticated and current_user != poll.creator:
        flash('You do not have permission to view this poll', 'danger')
        return redirect(url_for('index'))
    
    # Get vote counts for each option
    vote_counts = {}
    for option in poll.options:
        vote_counts[option.id] = Vote.query.filter_by(option_id=option.id).count()
    
    # Check if user has already voted
    has_voted = False
    if current_user.is_authenticated:
        has_voted = Vote.query.filter_by(poll_id=poll_id, user_id=current_user.id).first() is not None
    
    return render_template('view_poll.html', 
                         poll=poll, 
                         vote_counts=vote_counts,
                         has_voted=has_voted)

@app.route('/vote/<int:poll_id>', methods=['POST'])
def vote(poll_id):
    if not current_user.is_authenticated:
        flash('Please log in to vote on this poll.', 'info')
        return redirect(url_for('login', next=url_for('view_poll', poll_id=poll_id)))
        
    poll = Poll.query.get_or_404(poll_id)
    option_id = request.form.get('option')
    
    if not option_id:
        flash('Please select an option to vote.', 'error')
        return redirect(url_for('view_poll', poll_id=poll_id))
    
    # Check if user has already voted
    existing_vote = Vote.query.filter_by(user_id=current_user.id, poll_id=poll_id).first()
    if existing_vote:
        return redirect(url_for('view_poll', poll_id=poll_id))
    
    vote = Vote(user_id=current_user.id, poll_id=poll_id, option_id=option_id)
    db.session.add(vote)
    db.session.commit()
    
    return redirect(url_for('view_poll', poll_id=poll_id))

@app.route('/my_polls')
@login_required
def my_polls():
    created_polls = Poll.query.filter_by(user_id=current_user.id).all()
    voted_polls = Poll.query.join(Vote).filter(Vote.user_id == current_user.id).all()
    return render_template('my_polls.html', created_polls=created_polls, voted_polls=voted_polls)

@app.route('/poll/<int:poll_id>/delete', methods=['POST'])
@login_required
def delete_poll(poll_id):
    poll = Poll.query.get_or_404(poll_id)
    
    if poll.user_id != current_user.id:
        flash('You can only delete your own polls.', 'error')
        return redirect(url_for('view_poll', poll_id=poll_id))
    
    db.session.delete(poll)
    db.session.commit()
    flash('Poll deleted successfully!', 'success')
    return redirect(url_for('my_polls'))

if __name__ == '__main__':
    app.run(debug=True, port=5002) 