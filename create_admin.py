import json
import hashlib
import os

users_file = "users.json"

def add_user(username, password, is_admin=False):
    if os.path.exists(users_file):
        with open(users_file, "r") as f:
            users = json.load(f)
    else:
        users = {}

    if username in users:
        print(f"Benutzer '{username}' existiert bereits.")
        return

    password_hash = hashlib.sha256(password.encode()).hexdigest()
    users[username] = {"password": password_hash, "is_admin": is_admin}

    with open(users_file, "w") as f:
        json.dump(users, f, indent=2)

    print(f"Benutzer '{username}' erfolgreich hinzugefügt.")

if __name__ == "__main__":
    add_user("admin", "admin123", is_admin=True)
