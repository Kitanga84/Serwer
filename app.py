from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
import os, json
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "geheim_key"
UPLOAD_FOLDER = "uploads"
SHARED_FOLDER = os.path.join(UPLOAD_FOLDER, "shared")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SHARED_FOLDER, exist_ok=True)
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

@app.route("/", methods=["GET", "POST"])
def index():
    if "username" not in session:
        return redirect(url_for("login"))
    
    username = session["username"]
    user_folder = ensure_user_folder(username)

    if request.method == "POST":
        file = request.files.get("file")
        if not file or file.filename == "":
            flash("❌ Keine Datei ausgewählt.")
            return redirect(url_for("index"))

        filename = secure_filename(file.filename)
        target_folder = request.form.get("target")
        if target_folder == "shared":
            filepath = os.path.join(SHARED_FOLDER, filename)
        else:
            filepath = os.path.join(user_folder, filename)
        file.save(filepath)
        flash(f"✅ Datei '{filename}' wurde hochgeladen.")
        return redirect(url_for("index"))

    private_files = os.listdir(user_folder)
    shared_files = os.listdir(SHARED_FOLDER)

    return render_template("index.html", username=username,
                           private_files=private_files,
                           shared_files=shared_files)

@app.route('/uploads/<username>/<filename>')
def download_file(username, filename):
    user_folder = os.path.join(app.config['UPLOAD_FOLDER'], username)
    return send_from_directory(user_folder, filename, as_attachment=True)

@app.route('/uploads/shared/<filename>')
def download_shared_file(filename):
    return send_from_directory(SHARED_FOLDER, filename, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
