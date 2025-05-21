from app import init_db, create_default_admins

init_db()
create_default_admins()

print("✔️ Baza danych została utworzona. Konta admin1 i admin2 są gotowe.")
