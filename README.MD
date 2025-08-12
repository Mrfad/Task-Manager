# 🗂️ Django Task Manager

A simple yet powerful **Task Management** web application built with **Django**.  
Allows users to create, update, and manage tasks with a clean Bootstrap-based interface.

---

## Features
- Create, edit, and delete tasks
- Mark tasks as completed
- Categorize and filter tasks
- User authentication (login & signup)
- Responsive design with Bootstrap 5



## Installation

### 1. Clone the Repository

git clone https://github.com/Mrfad/Task-Manager.git
cd Task-Manager

### 2. Create & Activate Virtual Environment
python -m venv venv
source venv/bin/activate    # Linux / macOS
venv\Scripts\activate       # Windows

### 3. Install Dependencies
pip install -r requirements.txt

### 4. Environment Variables
cp .env-sample .env

### 5. Run Migrations
python manage.py migrate

### 6. Create Superuser (Optional)
python manage.py createsuperuser

### 7. Start Development Server
python manage.py runserver

Visit: http://127.0.0.1:8000/
