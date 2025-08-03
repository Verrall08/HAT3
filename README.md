# HAT3 - Quiz Game Application

## Overview

My website is a web-based quiz application built with Flask, a Python web framework. It is a quiz website that has admin and a user page. The users take quizzes and can track their scores. The admin pannel allows for them to create quizes, managing users, manage existing quizzes and provide feedback to users.

## Installation
1. Clone the repository
2. Install depedencies
3. Use the terminal to install the requirements

```bash
pip install -r requirements.txt
```
4. Run the program

```bash
python app.py
```

## Features

*   **User Authentication:** Secure user registration and login.
*   **Role-Based Access:** Admin and regular user roles with different privileges.
*   **Quiz Management:** Admins can create, assign, and manage quizzes.
*   **Quiz Taking:** Users can take assigned quizzes and submit answers.
*   **Score Tracking:** Users can view their scores on completed quizzes.
*   **Admin Panel:** Admins can manage users, quizzes, and mark submitted quizzes.
*   **Customizable Quizzes:** Support for multiple-choice and short answer questions.
*   **Responsive Design:** User interface adapts to different screen sizes.
*   **Theming:** Light and dark mode support.

## Technologies Used

*   **Flask:** Python web framework.
*   **Flask-Login:** User session management.
*   **SQLAlchemy:** Database ORM.
*   **WTForms:** Form handling and validation.
*   **Bootstrap:** CSS framework for styling.
*   **HTML/CSS/JavaScript:** Front-end technologies.