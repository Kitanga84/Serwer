from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dein_geheimes_schluessel'  # zmień na swoje silne hasło
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Model użytkownika
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

# Tworzenie tabeli przy pierwszym uruchomieniu
@app.before_first_request
def create_tables():
    db.create_all()

# Strona główna
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    return render_template('index.html', user=user)

# Logowanie
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            flash('Erfolgreich eingeloggt.', 'success')
            return redirect(url_for('index'))
        else:
            flash('Ungültiger Benutzername oder Passwort.', 'danger')
    return render_template('login.html')

# Wylogowanie
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Erfolgreich ausgeloggt.', 'info')
    return redirect(url_for('login'))

# Rejestracja - tylko dla admina
@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' not in session:
        flash('Bitte zuerst einloggen.', 'warning')
        return redirect(url_for('login'))
    current_user = User.query.get(session['user_id'])
    if not current_user.is_admin:
        flash('Keine Berechtigung.', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('Benutzername existiert bereits.', 'danger')
            return redirect(url_for('register'))
        hashed_pw = generate_password_hash(password)
        new_user = User(username=username, password=hashed_pw, is_admin=False)
        db.session.add(new_user)
        db.session.commit()
        flash('Benutzer erfolgreich erstellt.', 'success')
        return redirect(url_for('index'))
    return render_template('register.html')

# Tymczasowa trasa do utworzenia pierwszego admina
@app.route('/create_admin')
def create_admin():
    if User.query.filter_by(username='admin1').first():
        return "Admin existiert schon"
    hashed_pw = generate_password_hash('deinpasswort123')
    admin = User(username='admin1', password=hashed_pw, is_admin=True)
    db.session.add(admin)
    db.session.commit()
    return "Admin wurde erstellt! Bitte entferne / deaktiviere diese Route nach Gebrauch."

if __name__ == '__main__':
    app.run(debug=True)
