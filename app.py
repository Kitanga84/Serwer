import os
import json
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'supersecretkey'

UPLOAD_FOLDER = 'uploads'
SHARED_FOLDER = os.path.join(UPLOAD_FOLDER, 'shared')
USER_FILE = 'users.json'
HISTORY_FILE = 'download_history.json'
OWNERS_FILE = 'file_owners.json'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SHARED_FOLDER, exist_ok=True)

ADMINS = ['admin1', 'admin2']

def load_data(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    return {} if filename != HISTORY_FILE else []

def save_data(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    username = session['username']
    private_files = os.listdir(os.path.join(UPLOAD_FOLDER, username)) if os.path.exists(os.path.join(UPLOAD_FOLDER, username)) else []
    shared_files = os.listdir(SHARED_FOLDER) if os.path.exists(SHARED_FOLDER) else []
    return render_template('index.html', username=username, private_files=private_files, shared_files=shared_files)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = load_data(USER_FILE)
        if username in users:
            flash('Benutzername existiert bereits.', 'danger')
            return redirect(url_for('register'))
        users[username] = generate_password_hash(password)
        save_data(USER_FILE, users)
        os.makedirs(os.path.join(UPLOAD_FOLDER, username), exist_ok=True)
        flash('Registrierung erfolgreich. Bitte anmelden.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = load_data(USER_FILE)
        if username in users and check_password_hash(users[username], password):
            session['username'] = username
            flash('Anmeldung erfolgreich.', 'success')
            return redirect(url_for('index'))
        flash('Ungültiger Benutzername oder Passwort.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Abgemeldet.', 'info')
    return redirect(url_for('login'))

@app.route('/upload', methods=['POST'])
def upload():
    if 'username' not in session:
        return redirect(url_for('login'))
    file = request.files['file']
    target = request.form['target']
    username = session['username']
    if file:
        filename = file.filename
        folder = SHARED_FOLDER if target == 'shared' else os.path.join(UPLOAD_FOLDER, username)
        os.makedirs(folder, exist_ok=True)
        file.save(os.path.join(folder, filename))
        if target == 'shared':
            owners = load_data(OWNERS_FILE)
            owners[filename] = username
            save_data(OWNERS_FILE, owners)
        flash('Datei erfolgreich hochgeladen.', 'success')
    return redirect(url_for('index'))

@app.route('/download/<folder>/<filename>')
def download(folder, filename):
    if 'username' not in session:
        return redirect(url_for('login'))
    username = session['username']
    path = os.path.join(UPLOAD_FOLDER, folder, filename)
    if not os.path.exists(path):
        flash('Datei nicht gefunden.', 'danger')
        return redirect(url_for('index'))
    history = load_data(HISTORY_FILE)
    history.append({"user": username, "file": filename, "from": folder, "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
    save_data(HISTORY_FILE, history)
    return send_from_directory(os.path.join(UPLOAD_FOLDER, folder), filename, as_attachment=True)

@app.route('/delete/<folder>/<filename>')
def delete_file(folder, filename):
    if 'username' not in session:
        return redirect(url_for('login'))
    username = session['username']
    path = os.path.join(UPLOAD_FOLDER, folder, filename)
    if folder == 'shared':
        if username in ADMINS:
            os.remove(path)
        else:
            owners = load_data(OWNERS_FILE)
            if filename in owners and owners[filename] == username:
                os.remove(path)
                del owners[filename]
                save_data(OWNERS_FILE, owners)
            else:
                flash('Du darfst diese Datei nicht löschen.', 'danger')
                return redirect(url_for('index'))
    else:
        if username == folder or username in ADMINS:
            os.remove(path)
        else:
            flash('Du darfst diese Datei nicht löschen.', 'danger')
            return redirect(url_for('index'))
    flash('Datei gelöscht.', 'success')
    return redirect(url_for('index'))

@app.route('/download_history')
def download_history():
    if 'username' not in session:
        return redirect(url_for('login'))
    history = load_data(HISTORY_FILE)
    return render_template('history.html', history=history)

@app.route('/admin/users')
def admin_users():
    if 'username' not in session or session['username'] not in ADMINS:
        flash('Zugriff verweigert.', 'danger')
        return redirect(url_for('index'))
    users = load_data(USER_FILE)
    return render_template('admin_users.html', users=users)

@app.route('/admin/delete_user/<username_to_delete>')
def delete_user(username_to_delete):
    if 'username' not in session or session['username'] not in ADMINS:
        flash('Zugriff verweigert.', 'danger')
        return redirect(url_for('index'))
    if username_to_delete in ADMINS:
        flash('Admins können nicht gelöscht werden.', 'danger')
        return redirect(url_for('admin_users'))
    users = load_data(USER_FILE)
    if username_to_delete in users:
        del users[username_to_delete]
        save_data(USER_FILE, users)
        user_folder = os.path.join(UPLOAD_FOLDER, username_to_delete)
        if os.path.exists(user_folder):
            for f in os.listdir(user_folder):
                os.remove(os.path.join(user_folder, f))
            os.rmdir(user_folder)
        flash(f'Benutzer {username_to_delete} gelöscht.', 'success')
    else:
        flash('Benutzer nicht gefunden.', 'warning')
    return redirect(url_for('admin_users'))

if __name__ == '__main__':
    app.run(debug=True)


if __name__ == "__main__":
    app.run(debug=True)
