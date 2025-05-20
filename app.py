from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
import os, json
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "geheim_key"
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
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
    user_folder = os.path.join(app.config["UPLOAD_FOLDER"], username)
    os.makedirs(user_folder, exist_ok=True)
    return user_folder

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
        else:
            flash("❌ Falscher Benutzername oder Passwort.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("username", None)
    flash("👋 Abgemeldet.")
    return redirect(url_for("login"))

@app.route("/")
def index():
    if "username" not in session:
        return redirect(url_for("login"))
    username = session["username"]
    user_folder = ensure_user_folder(username)
    files = os.listdir(user_folder)
    return render_template("index.html", username=username, files=files)

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

@app.route('/download/<username>/<filename>')
def download_file(username, filename):
    user_folder = os.path.join(app.config["UPLOAD_FOLDER"], username)
    return send_from_directory(user_folder, filename, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)

