# Import Flask and related modules
from flask import Flask, render_template, redirect, url_for, flash, request, abort, current_app
from flask_login import (
    LoginManager,
    login_user,
    login_required,
    logout_user,
    current_user,
)

# Import your database model and forms
from models import db, User
from forms import RegisterForm, LoginForm, EditAccountForm
from config import Config   
from seed_db import seed_default_users
from models import Quiz, Question, QuizSubmission, QuizAssignments
import json
from sqlalchemy.orm import joinedload

# Create the Flask app instance
app = Flask(__name__)
app.config.from_object(Config)  # Load settings like SECRET_KEY and DB path

# Initialize the database with the app
db.init_app(app)

# Set up Flask-Login
login_manager = LoginManager(app)
login_manager.login_view = "login"  # Redirect to this route if login is required


@login_manager.user_loader
def load_user(user_id):
    """Load a user by ID for session tracking (used by Flask-Login)."""
    return db.session.get(User, int(user_id))


@app.route("/")
def home():
    """Redirect users from the home page to the dashboard."""
    return redirect(url_for("dashboard"))


@app.route("/register", methods=["GET", "POST"])
def register():
    """
    Register a new user.
    - Redirects to dashboard if already logged in.
    - Saves user to the database if form is valid.
    """
    if current_user.is_authenticated:
        return redirect(
            url_for("dashboard")
        )  # Don't allow already logged-in users to register again

    form = RegisterForm()
    # If the form was submitted (POST request) and passed all validation checks
    if form.validate_on_submit():
        # Create a new user and save to the database
        user = User(email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Log in an existing user.
    - Redirects to dashboard if already logged in.
    - Authenticates credentials and logs in the user.
    """
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        # Check if user exists and password is correct
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)  # Log in the user
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password", "danger")
    return render_template("login.html", form=form)


@app.route("/logout")
@login_required
def logout():
    """Log out the current user and redirect to the login page."""
    logout_user()
    return redirect(url_for("login"))

@app.route('/quiz')
@login_required
def quiz():
    quizzes = Quiz.query.filter(Quiz.assigned_users.any(id=current_user.id)).all()
    submitted_ids = set(
        str(sub.quiz_id) for sub in QuizSubmission.query.filter_by(id=current_user.id).all()
    )
    quizzes_to_show = [quiz for quiz in quizzes if str(quiz.id) not in submitted_ids]
    return render_template('quiz.html', quizzes=quizzes_to_show, submitted_ids=submitted_ids)

@app.route('/manage_quiz', methods=['GET', 'POST'])
@login_required
def manage_quiz():
    if not hasattr(current_user, 'is_admin') or not current_user.is_admin:
        return redirect(url_for('dashboard'))
    users = User.query.all()
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        num_questions_str = request.form.get('num_questions', '1')
        assigned_user_ids = request.form.getlist('assigned_users')
        try:
            num_questions = int(num_questions_str)
        except ValueError:
            num_questions = 1
        if not title or num_questions < 1:
            flash('Quiz title and number of questions are required.', 'danger')
            return redirect(url_for('manage_quiz'))
        quiz = Quiz(title=title)
        db.session.add(quiz)
        db.session.commit()
        for user_id in assigned_user_ids:
            user = User.query.get(int(user_id))
            if user:
                quiz.assigned_users.append(user)
        db.session.commit()  # Commit after assigning users

        # Add questions to the quiz
        for i in range(1, num_questions + 1):
            q_text = request.form.get(f'question_{i}', '').strip()
            q_type = request.form.get(f'type_{i}', 'multiple')
            points = int(request.form.get(f'points_{i}', '1'))
            if q_type == 'multiple':
                option_a = request.form.get(f'option_a_{i}', '')
                option_b = request.form.get(f'option_b_{i}', '')
                option_c = request.form.get(f'option_c_{i}', '')
                option_d = request.form.get(f'option_d_{i}', '')
                correct_option = request.form.get(f'correct_{i}', '')
                question = Question(
                    quiz_id=quiz.id,
                    text=q_text,
                    type=q_type,
                    option_a=option_a,
                    option_b=option_b,
                    option_c=option_c,
                    option_d=option_d,
                    correct_option=correct_option,
                    points=points
                )
            else:  # short answer
                question = Question(
                    quiz_id=quiz.id,
                    text=q_text,
                    type=q_type,
                    points=points
                )
            db.session.add(question)
        db.session.commit()  # Save all questions

        flash('Quiz created and sent to selected users!', 'success')
        return redirect(url_for('manage_quiz'))
    quizzes = Quiz.query.all()
    return render_template('manage_quiz.html', quizzes=quizzes, users=users)

@app.route('/delete_quiz/<int:quiz_id>', methods=['POST'])
@login_required
def delete_quiz(quiz_id):
    quiz = db.session.get(Quiz, quiz_id)
    if quiz is None:
        abort(404)
    # Delete all questions related to this quiz
    Question.query.filter_by(quiz_id=quiz.id).delete()
    Quiz.query.filter_by(id=quiz.id).delete()
    QuizSubmission.query.filter_by(quiz_id=quiz.id).delete()
    # how to delete the quiz assignments?
    db.session.commit()
    flash('Quiz and its questions have been deleted.', 'success')
    return redirect(url_for('existing_quizzes'))

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


@app.route("/account", methods=["GET", "POST"])
@login_required
def account():
    """
    Allow the logged-in user to update their email.
    - Shows a form prefilled with the current email.
    - Validates and saves new email if submitted.
    """
    # Prefill form with the current user's email
    form = EditAccountForm(original_email=current_user.email)
    if form.validate_on_submit():
        # Update the user's email
        current_user.email = form.email.data
        db.session.commit()
        flash("Your account has been updated.", "success")
        return redirect(url_for("account"))
    elif request.method == "GET":
        form.email.data = current_user.email  # Fill in the email when the page loads
    return render_template("edit_account.html", form=form)


@app.route("/users")
@login_required
def users():
    """
    Admin-only view of all registered users.
    - Redirects non-admins back to dashboard.
    """
    if not current_user.is_admin:
        flash("Access denied.", "danger")
        return redirect(url_for("dashboard"))

    # Show a list of all users in the system
    all_users = User.query.all()
    return render_template("users.html", users=all_users)


@app.route('/submit_quiz_for_review', methods=['POST'])
@login_required
def submit_quiz_for_review():
    quiz_id = request.form.get('quiz_id')
    existing = QuizSubmission.query.filter_by(user_id=current_user.id, quiz_id=quiz_id).first()
    if existing:
        flash("You have already submitted this quiz.", "info")
        return redirect(url_for('quiz'))
        
    # Save submission
    questions = Question.query.filter_by(quiz_id=quiz_id).all()
    answers = {str(q.id): request.form.get(f'question_{q.id}', '') for q in questions}
    submission = QuizSubmission(
        user_id=current_user.id,
        quiz_id=quiz_id,
        answers=answers
    )
    db.session.add(submission)
    db.session.commit()

    flash("Quiz submitted successfully for review!", "success")
    return redirect(url_for('quiz'))

@app.route('/admin/mark_quizzes')
def admin_mark_quizzes():
    submissions = QuizSubmission.query.filter_by(marked=False).all()
    #checck if submission is empty
    if submissions is None:
        flash("No quizzes to mark.", "info")
        return redirect(url_for('dashboard'))
    return render_template('admin_mark_quizzes.html', submissions=submissions)

@app.route('/admin/mark_quiz/<int:submission_id>', methods=['GET', 'POST'])
@login_required
def admin_mark_quiz(submission_id):
    if not current_user.is_admin:
        flash("Access denied.", "danger")
        return redirect(url_for("dashboard"))
    
    # Clear any stale data
    db.session.expire_all()
    
    # Load submission with all relationships
    submission = (
        QuizSubmission.query
        .options(
            joinedload(QuizSubmission.quiz),
            joinedload(QuizSubmission.user)
        )
        .get_or_404(submission_id)
    )
    
    if request.method == 'POST':
        total_score = 0
        for question in submission.quiz.questions:
            score_str = request.form.get(f'score_{question.id}', '0')
            try:
                score = int(score_str)
            except ValueError:
                score = 0
            score = max(0, min(score, question.points))
            total_score += score
        
        # Update submission with score and mark as complete
        submission.score = total_score
        submission.marked = True
        db.session.commit()
        
        flash(f"Quiz marked successfully. Total score: {total_score}", "success")
        return redirect(url_for('admin_mark_quizzes'))
    
    # Load questions separately to ensure they're fresh
    quiz = Quiz.query.options(joinedload(Quiz.questions)).get(submission.quiz_id)
    submission.quiz = quiz
    
    # Handle answers
    if isinstance(submission.answers, str):
        try:
            submission.answers = json.loads(submission.answers)
        except Exception:
            submission.answers = {}
    
    return render_template('admin_mark_quiz.html', submission=submission)

@app.route('/existing_quizzes')
@login_required
def existing_quizzes():
    if not hasattr(current_user, 'is_admin') or not current_user.is_admin:
        return redirect(url_for('dashboard'))
    quizzes = Quiz.query.all()
    return render_template('existing_quizzes.html', quizzes=quizzes)

@app.route("/my_scores")
@login_required
def my_scores():
    # Get all marked submissions for the current user
    marked_submissions = QuizSubmission.query.filter_by(
        user_id=current_user.id, 
        marked=True
    ).all()

    quizzes_to_delete = set()
    
    for submission in marked_submissions:
        quiz = submission.quiz
        if quiz:
            assigned_user_ids = [user.id for user in quiz.assigned_users]
            all_submissions = QuizSubmission.query.filter(
                QuizSubmission.quiz_id == quiz.id,
                QuizSubmission.user_id.in_(assigned_user_ids)
            ).all()
            # If all assigned users have a marked submission, delete the quiz
            if all(sub.marked for sub in all_submissions) and len(all_submissions) == len(assigned_user_ids):
                # quizzes_to_delete.add(quiz.id)
            
                db.session.commit()
    
    # Delete quizzes that all assigned users have marked submissions
    for quiz_id in quizzes_to_delete:
        db.session.execute(
            QuizAssignments.delete().where(QuizAssignments.c.quiz_id == quiz_id)
        )
        Question.query.filter_by(quiz_id=quiz_id).delete()
        QuizSubmission.query.filter_by(quiz_id=quiz_id).delete()
        Quiz.query.filter_by(id=quiz_id).delete()
    db.session.commit()
    
    return render_template("my_scores.html", submissions=marked_submissions)

if __name__ == "__main__":
    """
    Initialize the database, seed default users, and start the development server.
    This block runs only when this file is executed directly (not imported), i.e. "python app.py".
    """
    with app.app_context():
        db.create_all()  # Create tables if they don't exist
        seed_default_users()  # Add default admin and regular users

    app.run(debug=True)  # Start the server with debug mode (auto-reloads on changes)