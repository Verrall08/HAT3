from flask import render_template, request, redirect, url_for, flash
from models import Quiz, Question

@app.route('/quiz', methods=['GET', 'POST'])
@login_required
def quiz():
    quizzes = Quiz.query.all()
    if request.method == 'POST':
        score = 0
        total = 0
        for q in Question.query.filter_by(quiz_id=request.form['quiz_id']):
            total += 1
            user_answer = request.form.get(f'question_{q.id}')
            if user_answer == q.correct_option:
                score += 1
        flash(f'You scored {score} out of {total}', 'success')
        return redirect(url_for('quiz'))
    return render_template('quiz.html', quizzes=quizzes)

@app.route('/manage_quiz', methods=['GET', 'POST'])
@login_required
def manage_quiz():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        num_questions = int(request.form.get('num_questions', 1))
        if not title or num_questions < 1:
            flash('Quiz title and number of questions are required.', 'danger')
            return redirect(url_for('manage_quiz'))
        quiz = Quiz(title=title)
        db.session.add(quiz)
        db.session.commit()
        for i in range(1, num_questions + 1):
            q_text = request.form.get(f'question_{i}', '').strip()
            q_type = request.form.get(f'type_{i}', 'multiple')
            points = int(request.form.get(f'points_{i}', 1))
            if q_type == 'multiple':
                a = request.form.get(f'option_a_{i}', '').strip()
                b = request.form.get(f'option_b_{i}', '').strip()
                c = request.form.get(f'option_c_{i}', '').strip()
                d = request.form.get(f'option_d_{i}', '').strip()
                correct = request.form.get(f'correct_{i}', '').strip()
                if all([q_text, a, b, c, d, correct]):
                    question = Question(
                        quiz_id=quiz.id,
                        text=q_text,
                        type=q_type,
                        option_a=a,
                        option_b=b,
                        option_c=c,
                        option_d=d,
                        correct_option=correct,
                        points=points
                    )
                    db.session.add(question)
            else:
                if q_text:
                    question = Question(
                        quiz_id=quiz.id,
                        text=q_text,
                        type=q_type,
                        points=points
                    )
                    db.session.add(question)
        db.session.commit()
        flash('Quiz created and sent to users!', 'success')
        return redirect(url_for('manage_quiz'))
    quizzes = Quiz.query.all()
    return render_template('manage_quiz.html', quizzes=quizzes)