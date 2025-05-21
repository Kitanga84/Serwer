import os
import json
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'tajny_klucz'

UPLOAD_FOLDER = 'uploads'
SHARED_FOLDER = os.path.join(UPLOAD_FOLDER, 'shared')
HISTORY_FILE = 'download_history.json'
USER_FILE = 'users.json'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SHARED_FOLDER, exist_ok=True)

# Domyślni administratorzy
default_users = {
    "admin1": generate_password_hash("adminpass1"),
    "admin2": generate_password_hash("adminpass2")
}

# Inicjalizacja użytkowników
if not os.path.exists(USER_FILE):
    with open(USER_FILE, 'w') as f:
        json.dump(default_users, f)

# Inicjalizacja historii
if not os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, 'w') as f:
        json.dump([], f)

def load_users():
    with open(USER_FILE, 'r') as f:
        return json.load(f)

def save_users(users):
    with open(USER_FILE, 'w') as f:
        json.dump(users, f)

def save_history(entry):
    with open(HISTORY_FILE, 'r') as f:
        data = json.load(f)
    data.append(entry)
    with open(HISTORY_FILE, 'w') as f:
        json.dump(data, f, indent=2)

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    username = session['username']
    user_folder = os.path.join(UPLOAD_FOLDER, username)
    os.makedirs(user_folder, exist_ok=True)

    private_files = os.listdir(user_folder)
    shared_files = os.listdir(SHARED_FOLDER)

    with open(HISTORY_FILE) as f:
        history = json.load(f)

    return render_template('index.html', username=username, files=private_files, shared_files=shared_files, history=history)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        users = load_users()
        username = request.form['username']
        password = request.form['password']

        if username in users and check_password_hash(users[username], password):
            session['username'] = username
            return redirect(url_for('index'))
        flash('Nieprawidłowy login lub hasło')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'username' not in session or session['username'] not in ['admin1', 'admin2']:
        flash("Tylko administrator może dodawać użytkowników.")
        return redirect(url_for('index'))

    if request.method == 'POST':
        users = load_users()
        username = request.form['username']
        password = request.form['password']

        if username in users:
            flash("Użytkownik już istnieje.")
        else:
            users[username] = generate_password_hash(password)
            save_users(users)
            flash(f"Użytkownik {username} został dodany.")
            user_folder = os.path.join(UPLOAD_FOLDER, username)
            os.makedirs(user_folder, exist_ok=True)
            return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    file = request.files['file']
    target = request.form.get('target')

    if file.filename == '':
        flash("Brak pliku")
        return redirect(url_for('index'))

    folder = SHARED_FOLDER if target == 'shared' else os.path.join(UPLOAD_FOLDER, session['username'])
    file.save(os.path.join(folder, file.filename))
    flash("Plik zapisany")
    return redirect(url_for('index'))

@app.route('/download/<folder>/<filename>')
def download_file(folder, filename):
    if 'username' not in session:
        return redirect(url_for('login'))

    if folder == 'shared':
        folder_path = SHARED_FOLDER
    else:
        if session['username'] != folder:
            flash("Brak dostępu do tego folderu.")
            return redirect(url_for('index'))
        folder_path = os.path.join(UPLOAD_FOLDER, folder)

    save_history({
        "user": session['username'],
        "file": filename,
        "folder": folder,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

    return send_from_directory(folder_path, filename, as_attachment=True)

@app.route('/delete/<folder>/<filename>', methods=['POST'])
def delete_file(folder, filename):
    if 'username' not in session:
        return redirect(url_for('login'))

    if folder == 'shared':
        folder_path = SHARED_FOLDER
    else:
        if session['username'] != folder:
            flash("Brak dostępu do tego folderu.")
            return redirect(url_for('index'))
        folder_path = os.path.join(UPLOAD_FOLDER, folder)

    file_path = os.path.join(folder_path, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        flash("Plik usunięty")
    else:
        flash("Plik nie istnieje")
    return redirect(url_for('index'))

@app.route('/download_history')
def download_history():
    if 'username' not in session:
        return redirect(url_for('login'))

    with open(HISTORY_FILE) as f:
        history = json.load(f)
    return render_template('history.html', history=history)
