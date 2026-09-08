import sqlite3
from pathlib import Path


class Database:
    """Small SQLite repository that uses explicit SQL cursors for every operation."""

    def __init__(self, path="meedicoapp.db"):
        self.path = path

    def connect(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def init_db(self):
        Path(self.path).parent.mkdir(parents=True, exist_ok=True) if Path(self.path).parent != Path('.') else None
        with self.connect() as connection:
            cursor = connection.cursor()
            cursor.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'patient' CHECK(role IN ('patient', 'doctor', 'admin')),
                    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'inactive')),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS doctors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    specialty TEXT NOT NULL,
                    qualification TEXT NOT NULL,
                    experience INTEGER NOT NULL DEFAULT 0,
                    fee REAL NOT NULL DEFAULT 500,
                    available_days TEXT NOT NULL DEFAULT 'Mon, Wed, Fri',
                    avatar TEXT NOT NULL DEFAULT 'DR'
                );
                CREATE TABLE IF NOT EXISTS bookings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    doctor_id INTEGER NOT NULL REFERENCES doctors(id) ON DELETE CASCADE,
                    appointment_date TEXT NOT NULL,
                    appointment_time TEXT NOT NULL,
                    reason TEXT,
                    status TEXT NOT NULL DEFAULT 'confirmed',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cursor.execute("SELECT COUNT(*) AS count FROM users WHERE role = 'admin'")
            if cursor.fetchone()["count"] == 0:
                from werkzeug.security import generate_password_hash
                cursor.execute("INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)", ("Meedico Admin", "admin@meedicoapp.local", generate_password_hash("admin123"), "admin"))
            cursor.execute("SELECT COUNT(*) AS count FROM doctors")
            if cursor.fetchone()["count"] == 0:
                cursor.executemany("INSERT INTO doctors(name,specialty,qualification,experience,fee,available_days,avatar) VALUES(?,?,?,?,?,?,?)", [
                    ("Ananya Sharma", "General Medicine", "MBBS, MD", 12, 700, "Mon, Wed, Fri", "AS"),
                    ("Rohan Mehta", "Cardiology", "MBBS, DM", 15, 1200, "Tue, Thu, Sat", "RM"),
                    ("Kavya Iyer", "Dermatology", "MBBS, DDVL", 9, 900, "Mon, Tue, Thu", "KI"),
                ])

    def get_user(self, user_id):
        with self.connect() as connection:
            cursor = connection.cursor(); cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,)); return cursor.fetchone()

    def get_user_by_email(self, email):
        with self.connect() as connection:
            cursor = connection.cursor(); cursor.execute("SELECT * FROM users WHERE email = ?", (email,)); return cursor.fetchone()

    def create_user(self, name, email, password_hash, role="patient"):
        with self.connect() as connection:
            cursor = connection.cursor(); cursor.execute("INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)", (name, email, password_hash, role)); return cursor.lastrowid

    def list_users(self):
        with self.connect() as connection:
            cursor = connection.cursor(); cursor.execute("SELECT * FROM users ORDER BY created_at DESC"); return cursor.fetchall()

    def update_user(self, user_id, name, email, role, status):
        with self.connect() as connection:
            cursor = connection.cursor(); cursor.execute("UPDATE users SET name=?,email=?,role=?,status=? WHERE id=?", (name, email, role, status, user_id))

    def delete_user(self, user_id):
        with self.connect() as connection:
            cursor = connection.cursor(); cursor.execute("DELETE FROM users WHERE id=?", (user_id,))

    def list_doctors(self):
        with self.connect() as connection:
            cursor = connection.cursor(); cursor.execute("SELECT * FROM doctors ORDER BY name"); return cursor.fetchall()

    def get_doctor(self, doctor_id):
        with self.connect() as connection:
            cursor = connection.cursor(); cursor.execute("SELECT * FROM doctors WHERE id=?", (doctor_id,)); return cursor.fetchone()

    def create_booking(self, patient_id, doctor_id, date, time, reason):
        with self.connect() as connection:
            cursor = connection.cursor(); cursor.execute("INSERT INTO bookings(patient_id,doctor_id,appointment_date,appointment_time,reason) VALUES(?,?,?,?,?)", (patient_id, doctor_id, date, time, reason)); return cursor.lastrowid

    def get_booking(self, booking_id):
        with self.connect() as connection:
            cursor = connection.cursor(); cursor.execute("SELECT b.*, u.name AS patient_name, u.email AS patient_email, d.name AS doctor_name, d.specialty FROM bookings b JOIN users u ON u.id=b.patient_id JOIN doctors d ON d.id=b.doctor_id WHERE b.id=?", (booking_id,)); return cursor.fetchone()

    def list_bookings(self, user_id=None, limit=None):
        query = "SELECT b.*, u.name AS patient_name, d.name AS doctor_name, d.specialty FROM bookings b JOIN users u ON u.id=b.patient_id JOIN doctors d ON d.id=b.doctor_id"
        params = []
        if user_id is not None: query += " WHERE b.patient_id = ?"; params.append(user_id)
        query += " ORDER BY b.appointment_date DESC, b.appointment_time DESC"
        if limit: query += " LIMIT ?"; params.append(limit)
        with self.connect() as connection:
            cursor = connection.cursor(); cursor.execute(query, params); return cursor.fetchall()

    def dashboard_stats(self):
        with self.connect() as connection:
            cursor = connection.cursor(); cursor.execute("SELECT (SELECT COUNT(*) FROM users WHERE role='patient') AS patients, (SELECT COUNT(*) FROM doctors) AS doctors, (SELECT COUNT(*) FROM bookings) AS bookings, (SELECT COUNT(*) FROM bookings WHERE appointment_date = date('now')) AS today"); return cursor.fetchone()

    @staticmethod
    def public_user(user):
        return {"id": user["id"], "name": user["name"], "email": user["email"], "role": user["role"], "status": user["status"]}
