# Import SQLAlchemy for database interaction
from flask_sqlalchemy import SQLAlchemy

# Import UserMixin to provide default implementations for Flask-Login
from flask_login import UserMixin

# Import Werkzeug functions for password hashing (secure storage)
from werkzeug.security import generate_password_hash, check_password_hash

# Import datetime for timestamping submissions
from datetime import datetime

# Create a SQLAlchemy database instance
db = SQLAlchemy()


class User(UserMixin, db.Model):
    # Primary key: unique ID for each user
    id = db.Column(db.Integer, primary_key=True)

    # User's email address (must be unique and not empty)
    email = db.Column(db.String(120), unique=True, nullable=False)

    # Hashed password (not the plain text password!)
    password_hash = db.Column(db.String(128), nullable=False)

    # Boolean flag to mark admin users
    is_admin = db.Column(db.Boolean, default=False)

    # Hashes the password and stores it
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    # Checks if the given password matches the stored hash
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # String representation of the user object (for debugging)
    def __repr__(self):
        return f"<User {self.email}>"


class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    questions = db.relationship('Question', backref='quiz', lazy=True)


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    text = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(20), nullable=False, default='multiple')  # 'multiple', 'short', 'long'
    option_a = db.Column(db.String(100))
    option_b = db.Column(db.String(100))
    option_c = db.Column(db.String(100))
    option_d = db.Column(db.String(100))
    correct_option = db.Column(db.String(1))
    points = db.Column(db.Integer, default=1)


class QuizSubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    answers = db.Column(db.PickleType, nullable=False)  # Stores answers as a dict
    score = db.Column(db.Integer)
    marked = db.Column(db.Boolean, default=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='submissions')
    quiz = db.relationship('Quiz', backref='submissions')
