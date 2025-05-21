from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = "geheim_schlüssel"

UPLOAD_FOLDER = "uploads"
SHARED_FOLDER = os.path.join(UPLOAD_FOLDER, "shared")
HISTORY_FILE = "download_history.json"
USER_FILE = "users.json"

# Ordner vorbereiten
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SHARED_FOLDER, exist_ok=True)

# --- HILFSFUNKTIONEN --- #

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "username" not in session:
            flash("Bitte erst einloggen.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper

def load_users():
    if os.path.exists(USER_FILE):
        with open(USER_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USER_FILE, "w") as f:
        json.dump(users, f)

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return []

def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f)

# --- ROUTEN --- #

@app.route("/")
@login_required
def index():
    username = session["username"]
    user_folder = os.path.join(UPLOAD_FOLDER, username)
    os.makedirs(user_folder, exist_ok=True)

    user_files = os.listdir(user_folder)
    shared_files = os.listdir(SHARED_FOLDER)

    return render_template("index.html",
                           username=username,
                           user_files=user_files,
                           shared_files=shared_files)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        users = load_users()
        username = request.form["username"]
        password = request.form["password"]

        if username in users and check_password_hash(users[username], password):
            session["username"] = username
            flash("Erfolgreich eingeloggt.", "success")
            return redirect(url_for("index"))
        else:
            flash("Ungültige Anmeldedaten.", "danger")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("username", None)
    flash("Erfolgreich abgemeldet.", "info")
    return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
@login_required
def register():
    if session["username"] not in ["admin1", "admin2"]:
        flash("Nur Administratoren dürfen neue Benutzer erstellen.", "danger")
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if not username or not password:
            flash("Alle Felder müssen ausgefüllt werden.", "warning")
            return render_template("register.html")

        users = load_users()
        if username in users:
            flash("Benutzername ist bereits vergeben.", "danger")
        else:
            users[username] = generate_password_hash(password)
            save_users(users)
            os.makedirs(os.path.join(UPLOAD_FOLDER, username), exist_ok=True)
            flash(f"Benutzer '{username}' wurde erfolgreich erstellt.", "success")
            return redirect(url_for("index"))

    return render_template("register.html")

@app.route("/upload", methods=["POST"])
@login_required
def upload():
    if "file" not in request.files:
        flash("Keine Datei ausgewählt.", "warning")
        return redirect(url_for("index"))

    file = request.files["file"]
    if file.filename == "":
        flash("Dateiname fehlt.", "warning")
        return redirect(url_for("index"))

    target = request.form.get("target")
    if target == "shared":
        path = SHARED_FOLDER
    else:
        path = os.path.join(UPLOAD_FOLDER, session["username"])

    filename = secure_filename(file.filename)
    file.save(os.path.join(path, filename))
    flash("Datei erfolgreich hochgeladen.", "success")
    return redirect(url_for("index"))

@app.route("/download/<path:folder>/<filename>")
@login_required
def download(folder, filename):
    if folder == "shared":
        path = SHARED_FOLDER
    else:
        path = os.path.join(UPLOAD_FOLDER, folder)

    filepath = os.path.join(path, filename)
    if not os.path.exists(filepath):
        flash("Datei nicht gefunden.", "danger")
        return redirect(url_for("index"))

    history = load_history()
    history.append({
        "user": session["username"],
        "file": filename,
        "from": folder,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    save_history(history)

    return send_from_directory(path, filename, as_attachment=True)

@app.route("/delete/<path:folder>/<filename>")
@login_required
def delete_file(folder, filename):
    if folder == "shared":
        path = SHARED_FOLDER
    else:
        if folder != session["username"] and session["username"] not in ["admin1", "admin2"]:
            flash("Keine Berechtigung zum Löschen dieser Datei.", "danger")
            return redirect(url_for("index"))
        path = os.path.join(UPLOAD_FOLDER, folder)

    filepath = os.path.join(path, filename)
    if os.path.exists(filepath):
        os.remove(filepath)
        flash("Datei gelöscht.", "info")
    else:
        flash("Datei existiert nicht.", "warning")

    return redirect(url_for("index"))

@app.route("/download_history")
@login_required
def download_history():
    history = load_history()
    return render_template("history.html", history=history)

if __name__ == "__main__":
    app.run(debug=True)
