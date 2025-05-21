from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
import os
import json
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'tajny_klucz'

UPLOAD_FOLDER = 'uploads'
SHARED_FOLDER = os.path.join(UPLOAD_FOLDER, 'shared')
USERS_FILE = 'users.json'
HISTORY_FILE = 'history.json'

# Utwórz foldery jeśli nie istnieją
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SHARED_FOLDER, exist_ok=True)

# Inicjalizacja plików json jeśli nie istnieją
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, 'w') as f:
        json.dump({"admin": {"password": generate_password_hash("admin"), "is_admin": True}}, f)

if not os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, 'w') as f:
        json.dump([], f)

def load_users():
    with open(USERS_FILE) as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f)

def log_history(username, filename):
    with open(HISTORY_FILE, 'r') as f:
        history = json.load(f)
    history.append({"user": username, "file": filename, "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f)

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    private_path = os.path.join(UPLOAD_FOLDER, username)
    os.makedirs(private_path, exist_ok=True)

    files = os.listdir(private_path)
    shared_files = os.listdir(SHARED_FOLDER)

    with open(HISTORY_FILE) as f:
        history = json.load(f)

    return render_template('index.html', username=username, files=files, shared_files=shared_files, history=history)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'username' not in session or not load_users()[session['username']].get('is_admin'):
        flash("Tylko administrator może dodawać użytkowników.")
        return redirect(url_for('login'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = load_users()

        if username in users:
            flash('Użytkownik już istnieje.')
            return redirect(url_for('register'))

        users[username] = {
            'password': generate_password_hash(password),
            'is_admin': False
        }
        save_users(users)

        private_folder = os.path.join(UPLOAD_FOLDER, username)
        os.makedirs(private_folder, exist_ok=True)

        flash('Użytkownik dodany pomyślnie.')
        return redirect(url_for('index'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = load_users()

        if username in users and check_password_hash(users[username]['password'], password):
            session['username'] = username
            return redirect(url_for('index'))

        flash('Nieprawidłowe dane logowania.')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/upload', methods=['POST'])
def upload():
    if 'username' not in session:
        return redirect(url_for('login'))

    file = request.files['file']
    target = request.form['target']

    if target == 'shared':
        file.save(os.path.join(SHARED_FOLDER, file.filename))
    else:
        user_folder = os.path.join(UPLOAD_FOLDER, session['username'])
        os.makedirs(user_folder, exist_ok=True)
        file.save(os.path.join(user_folder, file.filename))

    flash('Plik został przesłany.')
    return redirect(url_for('index'))

@app.route('/download/<path:filename>/<source>')
def download_file(filename, source):
    if 'username' not in session:
        return redirect(url_for('login'))

    if source == 'shared':
        folder = SHARED_FOLDER
    else:
        folder = os.path.join(UPLOAD_FOLDER, session['username'])

    log_history(session['username'], filename)
    return send_from_directory(folder, filename, as_attachment=True)

@app.route('/delete/<path:filename>/<source>')
def delete_file(filename, source):
    if 'username' not in session:
        return redirect(url_for('login'))

    if source == 'shared':
        folder = SHARED_FOLDER
    else:
        folder = os.path.join(UPLOAD_FOLDER, session['username'])

    file_path = os.path.join(folder, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        flash('Plik został usunięty.')
    else:
        flash('Plik nie istnieje.')

    return redirect(url_for('index'))

@app.route('/download_history')
def download_history():
    if 'username' not in session:
        return redirect(url_for('login'))

    with open(HISTORY_FILE) as f:
        history = json.load(f)

    return render_template('history.html', history=history)

if __name__ == '__main__':
    app.run(debug=True)
