from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
import os, json
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey"

UPLOAD_FOLDER = "uploads"
SHARED_FOLDER = os.path.join(UPLOAD_FOLDER, "shared")
HISTORY_FILE = "history.json"
USERS_FILE = "users.json"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SHARED_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

def load_users():
    return json.load(open(USERS_FILE)) if os.path.exists(USERS_FILE) else {}

def save_users(users):
    json.dump(users, open(USERS_FILE, "w"), indent=2)

def load_history():
    return json.load(open(HISTORY_FILE)) if os.path.exists(HISTORY_FILE) else []

def save_history(history):
    json.dump(history, open(HISTORY_FILE, "w"), indent=2)

def ensure_user_folder(username):
    user_folder = os.path.join(UPLOAD_FOLDER, username)
    os.makedirs(user_folder, exist_ok=True)
    return user_folder

@app.route("/")
def index():
    if "username" not in session:
        return redirect(url_for("login"))
    username = session["username"]
    user_folder = ensure_user_folder(username)
    files = os.listdir(user_folder)
    shared_files = os.listdir(SHARED_FOLDER)
    history = load_history()
    return render_template("index.html", username=username, files=files, shared_files=shared_files, history=history)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        users = load_users()
        if username in users:
            flash("❌ Benutzer existiert bereits.")
        else:
            users[username] = password
            save_users(users)
            flash("✅ Registrierung erfolgreich.")
            return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        users = load_users()
        if users.get(username) == password:
            session["username"] = username
            return redirect(url_for("index"))
        flash("❌ Falsche Daten.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))

@app.route("/upload", methods=["POST"])
def upload():
    if "username" not in session:
        return redirect(url_for("login"))
    file = request.files["file"]
    if not file or file.filename == "":
        flash("❌ Keine Datei gewählt.")
        return redirect(url_for("index"))

    destination = request.form.get("destination", "private")
    filename = secure_filename(file.filename)

    if destination == "shared":
        folder = SHARED_FOLDER
    else:
        folder = ensure_user_folder(session["username"])

    file.save(os.path.join(folder, filename))
    flash(f"✅ Datei '{filename}' hochgeladen.")
    return redirect(url_for("index"))

@app.route("/download/<path:filename>")
def download_file(filename):
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]
    user_folder = ensure_user_folder(username)

    if os.path.exists(os.path.join(user_folder, filename)):
        folder = user_folder
    elif os.path.exists(os.path.join(SHARED_FOLDER, filename)):
        folder = SHARED_FOLDER
    else:
        flash("❌ Datei nicht gefunden.")
        return redirect(url_for("index"))

    # Zapis do historii
    history = load_history()
    history.append({
        "user": username,
        "filename": filename,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    save_history(history)

    return send_from_directory(folder, filename, as_attachment=True)

@app.route("/delete/<path:filename>")
def delete_file(filename):
    if "username" not in session:
        return redirect(url_for("login"))
    username = session["username"]
    user_folder = ensure_user_folder(username)

    # Usuwanie tylko z folderu prywatnego użytkownika
    filepath = os.path.join(user_folder, filename)
    if os.path.exists(filepath):
        os.remove(filepath)
        flash(f"🗑️ Datei '{filename}' gelöscht.")
    else:
        flash("❌ Datei nicht gefunden.")
    return redirect(url_for("index"))

@app.route("/download_history")
def download_history():
    if "username" not in session:
        return redirect(url_for("login"))
    username = session["username"]
    history = [h for h in load_history() if h["user"] == username]
    return render_template("history.html", history=history)
