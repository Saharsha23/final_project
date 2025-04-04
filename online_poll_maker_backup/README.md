# Poll Maker

A modern web application for creating and participating in polls with real-time results visualization.

## Features

- User authentication (login/register)
- Create polls with multiple options
- Vote on polls
- Real-time results visualization with pie charts
- Modern and responsive UI
- SQL database integration

## Setup Instructions

1. Make sure you have Python 3.8+ installed
2. Install XAMPP and start the MySQL service
3. Create a new database named `poll_maker` in phpMyAdmin
4. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```
5. Create a `.env` file in the project root with the following content:
   ```
   SECRET_KEY=your-secret-key-here
   ```
6. Run the application:
   ```bash
   python app.py
   ```
7. Open your browser and navigate to `http://localhost:5000`

## Usage

1. Register a new account or login with existing credentials
2. Create a new poll by clicking the "Create Poll" button
3. Add a title, description, and multiple options
4. Share the poll URL with others
5. View real-time results with interactive charts

## Technologies Used

- Flask (Python web framework)
- SQLAlchemy (Database ORM)
- MySQL (Database)
- Bootstrap 5 (Frontend framework)
- Chart.js (Data visualization)
- Flask-Login (User authentication)