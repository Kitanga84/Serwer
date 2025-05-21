from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
import os, json
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.secret_key = "geheim_key"

UPLOAD_FOLDER = "uploads"
SHARED_FOLDER = os.path.join(UPLOAD_FOLDER, "shared")
HISTORY_FILE = "download_history.json"
USERS_FILE = "users.json"

# Utwórz wymagane foldery
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SHARED_FOLDER, exist_ok=True)
if not os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, "w") as f:
        json.dump([], f)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def ensure_user_folder(username):
    user_folder = os.path.join(app.config["UPLOAD_FOLDER"], username)
    os.makedirs(user_folder, exist_ok=True)
    return user_folder

def save_download_history(username, filename, folder):
    with open(HISTORY_FILE, "r") as f:
        history = json.load(f)
    history.append({
        "username": username,
        "filename": filename,
        "folder": folder,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

def load_download_history():
    with open(HISTORY_FILE, "r") as f:
        return json.load(f)

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

@app.route("/", methods=["GET"])
def index():
    if "username" not in session:
        return redirect(url_for("login"))
    username = session["username"]
    user_folder = ensure_user_folder(username)
    files = os.listdir(user_folder)
    shared_files = os.listdir(SHARED_FOLDER)
    history = load_download_history()
    return render_template("index.html", username=username, files=files, shared_files=shared_files, history=history)

@app.route("/upload", methods=["POST"])
def upload_file():
    if "username" not in session:
        return redirect(url_for("login"))
    if "file" not in request.files:
        flash("❌ Keine Datei ausgewählt.")
        return redirect(url_for("index"))
    file = request.files["file"]
    if file.filename == "":
        flash("❌ Keine Datei ausgewählt.")
        return redirect(url_for("index"))
    username = session["username"]
    filename = secure_filename(file.filename)
    user_folder = ensure_user_folder(username)
    filepath = os.path.join(user_folder, filename)
    file.save(filepath)
    flash(f"✅ Datei '{filename}' wurde hochgeladen.")
    return redirect(url_for("index"))

@app.route("/upload/shared", methods=["POST"])
def upload_shared_file():
    if "username" not in session:
        return redirect(url_for("login"))
    if "file" not in request.files:
        flash("❌ Keine Datei ausgewählt.")
        return redirect(url_for("index"))
    file = request.files["file"]
    if file.filename == "":
        flash("❌ Keine Datei ausgewählt.")
        return redirect(url_for("index"))
    filename = secure_filename(file.filename)
    filepath = os.path.join(SHARED_FOLDER, filename)
    file.save(filepath)
    flash(f"✅ Datei '{filename}' im gemeinsamen Ordner gespeichert.")
    return redirect(url_for("index"))

@app.route("/download/<username>/<filename>")
def download_file(username, filename):
    if "username" not in session or session["username"] != username:
        flash("❌ Zugriff verweigert.")
        return redirect(url_for("index"))
    user_folder = ensure_user_folder(username)
    save_download_history(session["username"], filename, "privat")
    return send_from_directory(user_folder, filename, as_attachment=True)

@app.route("/download/shared/<filename>")
def download_shared_file(filename):
    if "username" not in session:
        return redirect(url_for("login"))
    save_download_history(session["username"], filename, "shared")
    return send_from_directory(SHARED_FOLDER, filename, as_attachment=True)

@app.route("/delete/<folder>/<filename>", methods=["POST"])
def delete_file(folder, filename):
    if "username" not in session:
        return redirect(url_for("login"))
    if folder == "shared":
        path = os.path.join(SHARED_FOLDER, filename)
    else:
        if session["username"] != folder:
            flash("❌ Zugriff verweigert.")
            return redirect(url_for("index"))
        path = os.path.join(UPLOAD_FOLDER, folder, filename)
    if os.path.exists(path):
        os.remove(path)
        flash(f"🗑️ Datei '{filename}' gelöscht.")
    else:
        flash("❌ Datei nicht gefunden.")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
