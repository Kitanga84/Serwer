import os
import json
import hashlib
import psutil
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'supersecretkey'

UPLOAD_FOLDER = 'uploads'
SHARED_FOLDER = os.path.join(UPLOAD_FOLDER, 'shared')
STATIC_BACKGROUND_FOLDER = 'static/backgrounds'
USER_FILE = 'users.json'
HISTORY_FILE = 'download_history.json'
OWNERS_FILE = 'file_owners.json'
SETTINGS_FILE = 'settings.json'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SHARED_FOLDER, exist_ok=True)
os.makedirs(STATIC_BACKGROUND_FOLDER, exist_ok=True)

ADMINS = ['admin1', 'admin2']

def load_data(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    return {} if filename != HISTORY_FILE else []

def save_data(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

def load_settings():
    return load_data(SETTINGS_FILE)

def save_settings(settings):
    save_data(SETTINGS_FILE, settings)

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    username = session['username']
    private_path = os.path.join(UPLOAD_FOLDER, username)
    shared_files = []
    private_files = []

    if os.path.exists(SHARED_FOLDER):
        for f in os.listdir(SHARED_FOLDER):
            size = os.path.getsize(os.path.join(SHARED_FOLDER, f))
            shared_files.append({'name': f, 'size': round(size / (1024**2), 2)})

    if os.path.exists(private_path):
        for f in os.listdir(private_path):
            size = os.path.getsize(os.path.join(private_path, f))
            private_files.append({'name': f, 'size': round(size / (1024**2), 2)})

    usage = psutil.disk_usage('/')
    free_gb = round(usage.free / (1024**3), 2)

    return render_template('index.html',
                           username=username,
                           private_files=private_files,
                           shared_files=shared_files,
                           free_gb=free_gb)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'username' not in session or session['username'] not in ADMINS:
        flash('Nur Administratoren können Benutzer hinzufügen.', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = load_data(USER_FILE)

        if username in users:
            flash('Benutzername existiert bereits.', 'danger')
            return redirect(url_for('register'))

        password_hash = hashlib.sha256(password.encode()).hexdigest()
        users[username] = {
            "password": password_hash,
            "is_admin": username in ADMINS
        }
        save_data(USER_FILE, users)
        os.makedirs(os.path.join(UPLOAD_FOLDER, username), exist_ok=True)
        flash('Benutzer erfolgreich erstellt.', 'success')
        return redirect(url_for('admin_users'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    settings = load_settings()
    background = settings.get('background', 'default.jpg')

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = load_data(USER_FILE)

        if username in users:
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            if users[username]['password'] == password_hash:
                session['username'] = username
                session['is_admin'] = users[username].get('is_admin', False)
                flash('Anmeldung erfolgreich.', 'success')
                return redirect(url_for('index'))
            else:
                flash('Falsches Passwort.', 'danger')
        else:
            flash('Benutzername existiert nicht.', 'danger')
    return render_template('login.html', background=background)

@app.route('/logout')
def logout():
    session.clear()
    flash('Abgemeldet.', 'info')
    return redirect(url_for('login'))

@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if new_password != confirm_password:
            flash('Neue Passwörter stimmen nicht überein.', 'danger')
            return redirect(url_for('change_password'))

        users = load_data(USER_FILE)
        username = session['username']
        current_hash = hashlib.sha256(current_password.encode()).hexdigest()

        if users[username]['password'] != current_hash:
            flash('Falsches aktuelles Passwort.', 'danger')
            return redirect(url_for('change_password'))

        new_hash = hashlib.sha256(new_password.encode()).hexdigest()
        users[username]['password'] = new_hash
        save_data(USER_FILE, users)
        flash('Passwort erfolgreich geändert.', 'success')
        return redirect(url_for('index'))

    return render_template('change_password.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'username' not in session:
        return redirect(url_for('login'))

    file = request.files.get('file')
    target = request.form.get('target')
    username = session['username']

    if not file or file.filename == '':
        flash('Keine Datei ausgewählt.', 'warning')
        return redirect(url_for('index'))

    filename = file.filename
    folder = SHARED_FOLDER if target == 'shared' else os.path.join(UPLOAD_FOLDER, username)
    os.makedirs(folder, exist_ok=True)
    file_path = os.path.join(folder, filename)
    file.save(file_path)

    if target == 'shared':
        owners = load_data(OWNERS_FILE)
        owners[filename] = username
        save_data(OWNERS_FILE, owners)

    # ✅ Zapis do historii (UPLOAD)
    history = load_data(HISTORY_FILE)
    history.append({
        "user": username,
        "file": filename,
        "from": target,
        "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "action": "upload"
    })
    save_data(HISTORY_FILE, history)

    flash(f'Datei "{filename}" erfolgreich hochgeladen.', 'success')
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

    # ✅ Zapis do historii (DOWNLOAD)
    history = load_data(HISTORY_FILE)
    history.append({
        "user": username,
        "file": filename,
        "from": folder,
        "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "action": "download"
    })
    save_data(HISTORY_FILE, history)

    return send_from_directory(os.path.join(UPLOAD_FOLDER, folder), filename, as_attachment=True)

@app.route('/delete/<folder>/<filename>')
def delete_file(folder, filename):
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    path = os.path.join(UPLOAD_FOLDER, folder, filename)

    if not os.path.exists(path):
        flash('Datei nicht gefunden.', 'danger')
        return redirect(url_for('index'))

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

@app.route('/admin/clear_history')
def clear_history():
    if 'username' not in session or session['username'] not in ADMINS:
        flash('Zugriff verweigert.', 'danger')
        return redirect(url_for('index'))
    save_data(HISTORY_FILE, [])
    flash('Download-Verlauf wurde gelöscht.', 'success')
    return redirect(url_for('download_history'))

@app.route('/admin/delete_history_entry/<int:entry_id>')
def delete_history_entry(entry_id):
    if 'username' not in session or session['username'] not in ADMINS:
        flash('Zugriff verweigert.', 'danger')
        return redirect(url_for('index'))
    history = load_data(HISTORY_FILE)
    if 0 <= entry_id < len(history):
        del history[entry_id]
        save_data(HISTORY_FILE, history)
        flash('Eintrag aus dem Verlauf gelöscht.', 'success')
    else:
        flash('Eintrag nicht gefunden.', 'danger')
    return redirect(url_for('download_history'))

@app.route('/admin/background', methods=['GET', 'POST'])
def upload_background():
    if 'username' not in session or session['username'] not in ADMINS:
        flash('Zugriff verweigert.', 'danger')
        return redirect(url_for('index'))

    background_files = os.listdir(STATIC_BACKGROUND_FOLDER)

    if request.method == 'POST':
        selected = request.form.get('selected_background')
        if selected and selected in background_files:
            settings = load_settings()
            settings['background'] = selected
            save_settings(settings)
            flash('Hintergrund erfolgreich gewechselt.', 'success')
        else:
            file = request.files.get('background')
            if file and file.filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                save_path = os.path.join(STATIC_BACKGROUND_FOLDER, file.filename)
                file.save(save_path)
                flash('Neues Hintergrundbild hochgeladen.', 'success')
            else:
                flash('Ungültige Datei. Bitte JPG oder PNG hochladen.', 'danger')
        return redirect(url_for('upload_background'))

    return render_template('upload_background.html', backgrounds=background_files)

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

@app.route('/admin/delete_background/<filename>')
def delete_background(filename):
    if 'username' not in session or session['username'] not in ADMINS:
        flash('Zugriff verweigert.', 'danger')
        return redirect(url_for('index'))

    settings = load_settings()
    current_background = settings.get('background', 'default.jpg')

    if filename == current_background:
        flash('Das aktuell verwendete Hintergrundbild kann nicht gelöscht werden.', 'warning')
        return redirect(url_for('upload_background'))

    file_path = os.path.join(STATIC_BACKGROUND_FOLDER, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        flash(f'Hintergrundbild "{filename}" wurde gelöscht.', 'success')
    else:
        flash('Datei nicht gefunden.', 'danger')

    return redirect(url_for('upload_background'))

if __name__ == '__main__':
    app.run(debug=True)
