import sqlite3
from werkzeug.security import generate_password_hash

DATABASE = 'users.db'

def run_init():
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
                c.execute("INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)",
                          (username, hashed_pw, 1))
                print(f"Utworzono domyślnego administratora: {username}")
            except sqlite3.IntegrityError:
                pass
        conn.commit()
