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
    # Get all quizzes assigned to the user and not hidden/deleted
    quizzes = Quiz.query.filter(
        Quiz.assigned_users.any(id=current_user.id),
        Quiz.hidden == False  # or Quiz.deleted == False if you use 'deleted'
    ).all()
    # Get IDs of quizzes the user has already submitted
    submitted_ids = set(
        sub.quiz_id for sub in QuizSubmission.query.filter_by(user_id=current_user.id).all()
    )
    # Only show quizzes the user has NOT submitted
    quizzes_to_show = [quiz for quiz in quizzes if quiz.id not in submitted_ids]
    return render_template('quiz.html', quizzes=quizzes_to_show)

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
        if not assigned_user_ids:
            flash('You must assign the quiz to at least one user.', 'danger')
            return
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
    quizzes = Quiz.query.filter_by(hidden=False).all()
    return render_template('manage_quiz.html', quizzes=quizzes, users=users)

@app.route('/delete_quiz/<int:quiz_id>', methods=['POST'])
@login_required
def delete_quiz(quiz_id):
    quiz = db.session.get(Quiz, quiz_id)
    if quiz is None:
        abort(404)
    # Soft delete: set hidden=True for quiz, its questions, assignments, and submissions
    quiz.hidden = True
    for question in Question.query.filter_by(quiz_id=quiz.id).all():
        question.hidden = True
    for submission in QuizSubmission.query.filter_by(quiz_id=quiz.id).all():
        submission.hidden = True
    # For assignments, if it's a table, use an update statement
    db.session.execute(
        QuizAssignments.update().where(QuizAssignments.c.quiz_id == quiz.id).values(hidden=True)
    )
    db.session.commit()
    flash('Quiz and its questions have been hidden.', 'success')
    return redirect(url_for('existing_quizzes'))

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


@app.route("/account", methods=["GET", "POST"])
@login_required
def account():
    """
    Allow the logged-in user to update their email and password.
    - Shows a form prefilled with the current email.
    - Validates and saves new email if submitted.
    - Handles password change if fields are filled.
    """
    form = EditAccountForm(original_email=current_user.email)
    if form.validate_on_submit():
        # Update email if changed
        if form.email.data != current_user.email:
            current_user.email = form.email.data
            db.session.commit()
            flash("Your email has been updated.", "success")

        # Handle password change if fields are filled
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if current_password or new_password or confirm_password:
            if not current_user.check_password(current_password):
                flash("Current password is incorrect.", "danger")
                return render_template("edit_account.html", form=form)
            if not new_password:
                flash("New password cannot be empty.", "danger")
                return render_template("edit_account.html", form=form)
            if new_password != confirm_password:
                flash("New passwords do not match.", "danger")
                return render_template("edit_account.html", form=form)
            if len(new_password) < 6:
                flash("New password must be at least 6 characters.", "danger")
                return render_template("edit_account.html", form=form)
            current_user.set_password(new_password)
            db.session.commit()
            flash("Your password has been updated.", "success")

        return redirect(url_for("account"))
    elif request.method == "GET":
        form.email.data = current_user.email
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
    quizzes = Quiz.query.filter_by(hidden=False).all()
    return render_template('existing_quizzes.html', quizzes=quizzes)

@app.route("/my_scores")
@login_required
def my_scores():
    # Get all marked submissions for the current user
    marked_submissions = QuizSubmission.query.filter_by(
        user_id=current_user.id, 
        marked=True,
        hidden=False
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

@app.route('/toggle_quiz_visibility/<int:quiz_id>', methods=['POST'])
@login_required
def toggle_quiz_visibility(quiz_id):
    if not current_user.is_admin:
        abort(403)
    quiz = db.session.get(Quiz, quiz_id)
    if not quiz:
        abort(404)
    quiz.hidden = not quiz.hidden
    db.session.commit()
    return redirect(url_for('existing_quizzes'))

@app.route('/toggle_score_visibility/<int:submission_id>', methods=['POST'])
@login_required
def toggle_score_visibility(submission_id):
    submission = QuizSubmission.query.get_or_404(submission_id)
    if submission.user_id != current_user.id:
        abort(403)
    submission.hidden = not submission.hidden
    db.session.commit()
    return redirect(url_for('my_scores'))

@app.route('/toggle_admin/<int:user_id>', methods=['POST'])
def toggle_admin(user_id):
    user = User.query.get(user_id)
    if user:
        # If trying to remove admin from the last admin, prevent it
        if user.is_admin:
            admin_count = User.query.filter_by(is_admin=True).count()
            if admin_count <= 1:
                flash("At least one user must remain an admin.", "danger")
                return redirect(url_for('users'))
        user.is_admin = not user.is_admin
        db.session.commit()
        flash(f"User {user.email} admin status changed.", "success")
    else:
        flash("User not found.", "danger")
    return redirect(url_for('users'))

if __name__ == "__main__":
    """
    Initialize the database, seed default users, and start the development server.
    This block runs only when this file is executed directly (not imported), i.e. "python app.py".
    """
    with app.app_context():
        db.create_all()  # Create tables if they don't exist
        seed_default_users()  # Add default admin and regular users

    app.run(debug=True)  # Start the server with debug mode (auto-reloads on changes)