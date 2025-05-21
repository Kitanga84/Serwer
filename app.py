from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, flash
from werkzeug.security import generate_password_hash, check_password_hash
import os
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'tajny_klucz'

UPLOAD_FOLDER = 'uploads'
SHARED_FOLDER = 'shared'
DATABASE = 'users.db'
HISTORY_LOG = 'download_history.log'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SHARED_FOLDER, exist_ok=True)

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL,
                        is_admin INTEGER NOT NULL)''')
    conn.commit()
    conn.close()

def create_default_admins():
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL,
                        is_admin INTEGER NOT NULL)''')
        admins = [("admin1", "admin1pass"), ("admin2", "admin2pass")]
        for username, password in admins:
            hashed_pw = generate_password_hash(password)
            try:
                c.execute("INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)", (username, hashed_pw, 1))
                print(f"Utworzono domyślnego administratora: {username}")
            except sqlite3.IntegrityError:
                pass
        conn.commit()

# 🚀 To działa także na Renderze, bo wykonuje się przy starcie
init_db()
create_default_admins()

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', username=session['username'], is_admin=session.get('is_admin', 0))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if not session.get('is_admin'):
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        is_admin = 1 if 'is_admin' in request.form else 0

        conn = get_db_connection()
        try:
            conn.execute("INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)",
                         (username, password, is_admin))
            conn.commit()
            os.makedirs(os.path.join(UPLOAD_FOLDER, username), exist_ok=True)
            flash('Użytkownik dodany pomyślnie.')
        except sqlite3.IntegrityError:
            flash('Nazwa użytkownika jest już zajęta.')
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['username'] = user['username']
            session['is_admin'] = user['is_admin']
            return redirect(url_for('index'))
        else:
            flash('Nieprawidłowy login lub hasło.')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/download/<folder>/<filename>')
def download_file(folder, filename):
    if 'username' not in session:
        return redirect(url_for('login'))
    filepath = os.path.join(folder, filename)
    if not os.path.exists(filepath):
        return "Plik nie istnieje", 404
    log_download(session['username'], filename)
    return send_from_directory(folder, filename, as_attachment=True)

def log_download(username, filename):
    with open(HISTORY_LOG, 'a') as f:
        f.write(f"{datetime.now()} - {username} pobrał {filename}\n")

@app.route('/download_history')
def download_history():
    if 'username' not in session:
        return redirect(url_for('login'))
    if not os.path.exists(HISTORY_LOG):
        history = []
    else:
        with open(HISTORY_LOG, 'r') as f:
            history = f.readlines()
    return render_template('history.html', history=history)

if __name__ == '__main__':
    app.run(debug=True)
