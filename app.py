from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
import os, json
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.secret_key = "geheim_key"
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, "shared"), exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
USERS_FILE = "users.json"

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def ensure_user_folder(username):
    folder = os.path.join(app.config["UPLOAD_FOLDER"], username)
    os.makedirs(folder, exist_ok=True)
    return folder

def log_download(username, filename, source):
    with open("downloads.log", "a") as f:
        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"{time} - {username} downloaded '{filename}' from {source}\n")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        users = load_users()
        if username in users:
            flash("❌ Benutzername existiert bereits.")
            return redirect(url_for("register"))
        users[username] = password
        save_users(users)
        flash("✅ Registrierung erfolgreich. Bitte einloggen.")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        users = load_users()
        if username in users and users[username] == password:
            session["username"] = username
            flash(f"👋 Willkommen, {username}!")
            return redirect(url_for("index"))
        flash("❌ Falscher Benutzername oder Passwort.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("username", None)
    flash("👋 Abgemeldet.")
    return redirect(url_for("login"))

@app.route("/upload", methods=["POST"])
def upload_file():
    if "username" not in session:
        return redirect(url_for("login"))
    file = request.files.get("file")
    location = request.form.get("location")
    if not file or file.filename == "":
        flash("❌ Keine Datei ausgewählt.")
        return redirect(url_for("index"))

    filename = secure_filename(file.filename)
    if location == "shared":
        folder = os.path.join(app.config["UPLOAD_FOLDER"], "shared")
    else:
        folder = ensure_user_folder(session["username"])

    os.makedirs(folder, exist_ok=True)
    file.save(os.path.join(folder, filename))
    flash(f"✅ Datei '{filename}' wurde hochgeladen.")
    return redirect(url_for("index"))

@app.route("/download/<username>/<filename>")
def download_file(username, filename):
    if "username" not in session or session["username"] != username:
        flash("⛔ Zugriff verweigert.")
        return redirect(url_for("index"))
    folder = ensure_user_folder(username)
    log_download(session["username"], filename, "private")
    return send_from_directory(folder, filename, as_attachment=True)

@app.route("/download/shared/<filename>")
def download_shared_file(filename):
    if "username" not in session:
        return redirect(url_for("login"))
    folder = os.path.join(app.config["UPLOAD_FOLDER"], "shared")
    log_download(session["username"], filename, "shared")
    return send_from_directory(folder, filename, as_attachment=True)

@app.route("/delete/<username>/<filename>")
def delete_file(username, filename):
    if "username" not in session or session["username"] != username:
        flash("⛔ Zugriff verweigert.")
        return redirect(url_for("index"))
    folder = ensure_user_folder(username)
    path = os.path.join(folder, filename)
    if os.path.exists(path):
        os.remove(path)
        flash(f"🗑️ Datei '{filename}' gelöscht.")
    return redirect(url_for("index"))

@app.route("/history")
def download_history():
    if "username" not in session:
        return redirect(url_for("login"))
    if not os.path.exists("downloads.log"):
        history = []
    else:
        with open("downloads.log", "r") as f:
            lines = f.readlines()
        history = [line.strip() for line in lines if session["username"] in line]
    return render_template("history.html", history=history)

@app.route("/")
def index():
    if "username" not in session:
        return redirect(url_for("login"))
    username = session["username"]
    user_folder = ensure_user_folder(username)
    user_files = os.listdir(user_folder)
    shared_folder = os.path.join(app.config["UPLOAD_FOLDER"], "shared")
    shared_files = os.listdir(shared_folder)
    return render_template("index.html", username=username, user_files=user_files, shared_files=shared_files)
