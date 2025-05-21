import json
import hashlib
import os

def add_user(username, password, is_admin=False):
    users_file = "users.json"

    if os.path.exists(users_file):
        with open(users_file, "r") as f:
            users = json.load(f)
    else:
        users = {}

    password_hash = hashlib.sha256(password.encode()).hexdigest()

    users[username] = {
        "password": password_hash,
        "is_admin": is_admin
    }

    with open(users_file, "w") as f:
        json.dump(users, f, indent=2)

    print(f"Użytkownik '{username}' został dodany. Admin: {is_admin}")

# Dodaj admina
add_user("admin", "admin123", is_admin=True)
