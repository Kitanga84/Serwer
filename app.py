from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
import os
import json
from functools import wraps
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'tajnyklucz'

UPLOAD_FOLDER = 'uploads'
SHARED_FOLDER = os.path.join(UPLOAD_FOLDER, 'shared')
PRIVATE_FOLDER = os.path.join(UPLOAD_FOLDER, 'private')
HISTORY_FILE = 'download_history.json'
USERS_FILE = 'users.json'

os.makedirs(SHARED_FOLDER, exist_ok=True)
os.makedirs(PRIVATE_FOLDER, exist_ok=True)

# Ładowanie użytkowników
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {}

# Zapis użytkowników
def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f)

# Historia pobrań
def log_download(username, filename, location):
    history = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            history = json.load(f)
    history.append({
        'username': username,
        'filename': filename,
        'location': location,
        'timestamp': datetime.now().isoformat()
    })
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f)

# Wymagaj logowania
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# Sprawdź, czy użytkownik to admin
def is_admin():
    return session.get('username') in ['admin1', 'admin2']

@app.route('/')
@login_required
def index():
    username = session['username']
    private_path = os.path.join(PRIVATE_FOLDER, username)
    os.makedirs(private_path, exist_ok=True)

    private_files = os.listdir(private_path)
    shared_files = os.listdir(SHARED_FOLDER)

    return render_template('index.html', username=username,
                           private_files=private_files,
                           shared_files=shared_files,
                           is_admin=is_admin())

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        users = load_users()
        username = request.form['username']
        password = request.form['password']
        if username in users and users[username] == password:
            session['username'] = username
            return redirect(url_for('index'))
        flash('Błędna nazwa użytkownika lub hasło.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    if not is_admin():
        flash('Tylko administrator może dodawać użytkowników.')
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = load_users()
        if username in users:
            flash('Użytkownik już istnieje.')
        else:
            users[username] = password
            save_users(users)
            os.makedirs(os.path.join(PRIVATE_FOLDER, username), exist_ok=True)
            flash('Użytkownik dodany pomyślnie.')
            return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/upload', methods=['POST'])
@login_required
def upload():
    file = request.files['file']
    folder = request.form['folder']
    username = session['username']

    if folder == 'private':
        path = os.path.join(PRIVATE_FOLDER, username)
    else:
        path = SHARED_FOLDER

    os.makedirs(path, exist_ok=True)
    file.save(os.path.join(path, file.filename))
    flash('Plik przesłany pomyślnie.')
    return redirect(url_for('index'))

@app.route('/download/<folder>/<filename>')
@login_required
def download(folder, filename):
    username = session['username']
    if folder == 'private':
        path = os.path.join(PRIVATE_FOLDER, username)
        if not os.path.exists(os.path.join(path, filename)):
            flash('Brak dostępu.')
            return redirect(url_for('index'))
    else:
        path = SHARED_FOLDER

    log_download(username, filename, folder)
    return send_from_directory(path, filename, as_attachment=True)

@app.route('/delete/<folder>/<filename>')
@login_required
def delete_file(folder, filename):
    username = session['username']
    if folder == 'private':
        path = os.path.join(PRIVATE_FOLDER, username)
    elif folder == 'shared':
        path = SHARED_FOLDER
    else:
        flash('Nieprawidłowy folder.')
        return redirect(url_for('index'))

    try:
        os.remove(os.path.join(path, filename))
        flash('Plik usunięty.')
    except:
        flash('Nie udało się usunąć pliku.')
    return redirect(url_for('index'))

@app.route('/download_history')
@login_required
def download_history():
    if not os.path.exists(HISTORY_FILE):
        history = []
    else:
        with open(HISTORY_FILE, 'r') as f:
            history = json.load(f)
    return render_template('history.html', history=history)

if __name__ == '__main__':
    app.run(debug=True)
