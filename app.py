import os
from datetime import timedelta
from functools import wraps

from flask import Flask, flash, jsonify, redirect, render_template, request, url_for
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_mail import Mail, Message
from werkzeug.security import check_password_hash, generate_password_hash

from models import Database


app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY", "change-this-secret-in-production"),
    JWT_SECRET_KEY=os.getenv("JWT_SECRET_KEY", "change-this-jwt-secret-in-production"),
    JWT_ACCESS_TOKEN_EXPIRES=timedelta(hours=8),
    MAIL_SERVER=os.getenv("MAIL_SERVER", "localhost"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", "25")),
    MAIL_USE_TLS=os.getenv("MAIL_USE_TLS", "false").lower() == "true",
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_DEFAULT_SENDER=os.getenv("MAIL_DEFAULT_SENDER", "noreply@meedicoapp.local"),
)

CORS(app, resources={r"/api/*": {"origins": os.getenv("CORS_ORIGINS", "*")}})
jwt = JWTManager(app)
mail = Mail(app)
db = Database(os.getenv("DATABASE_PATH", "meedicoapp.db"))


def current_user():
    user_id = request.cookies.get("user_id")
    return db.get_user(int(user_id)) if user_id and user_id.isdigit() else None


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user or user["role"] != "admin":
            flash("Administrator access is required.", "danger")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def send_booking_email(booking, patient, doctor):
    if not patient["email"]:
        return False
    try:
        msg = Message(
            subject=f"Meedicoapp booking confirmation #{booking['id']}",
            recipients=[patient["email"]],
            body=(f"Hello {patient['name']},\n\nYour appointment with Dr. {doctor['name']} "
                  f"is booked for {booking['appointment_date']} at {booking['appointment_time']}.\n\n"
                  "Thank you for using Meedicoapp."),
        )
        mail.send(msg)
        return True
    except Exception:
        app.logger.exception("Booking email could not be sent")
        return False


@app.context_processor
def inject_globals():
    return {"current_user": current_user()}


@app.route("/")
def index():
    return render_template("index.html", doctors=db.list_doctors(), bookings=db.list_bookings(limit=5))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name, email = request.form["name"].strip(), request.form["email"].strip().lower()
        if db.get_user_by_email(email):
            flash("An account with that email already exists.", "warning")
            return render_template("register.html")
        user_id = db.create_user(name, email, generate_password_hash(request.form["password"]), "patient")
        flash("Account created. Please sign in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = db.get_user_by_email(request.form["email"].strip().lower())
        if user and check_password_hash(user["password_hash"], request.form["password"]):
            response = redirect(url_for("admin_dashboard" if user["role"] == "admin" else "index"))
            response.set_cookie("user_id", str(user["id"]), httponly=True, samesite="Lax")
            flash(f"Welcome back, {user['name']}.", "success")
            return response
        flash("Invalid email or password.", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    response = redirect(url_for("index"))
    response.delete_cookie("user_id")
    flash("You have been signed out.", "info")
    return response


@app.route("/book", methods=["POST"])
def book_appointment():
    user = current_user()
    if not user:
        flash("Please sign in before booking an appointment.", "warning")
        return redirect(url_for("login"))
    try:
        doctor_id = int(request.form["doctor_id"])
        booking_id = db.create_booking(user["id"], doctor_id, request.form["appointment_date"], request.form["appointment_time"], request.form.get("reason", ""))
        booking = db.get_booking(booking_id)
        doctor = db.get_doctor(doctor_id)
        emailed = send_booking_email(booking, user, doctor)
        flash("Appointment confirmed." + (" Confirmation email sent." if emailed else ""), "success")
    except (KeyError, ValueError):
        flash("Please complete all appointment fields.", "danger")
    return redirect(url_for("index"))


@app.route("/admin")
@admin_required
def admin_dashboard():
    return render_template("admin/dashboard.html", stats=db.dashboard_stats(), bookings=db.list_bookings(), users=db.list_users(), doctors=db.list_doctors())


@app.route("/admin/users/<int:user_id>/update", methods=["POST"])
@admin_required
def update_user(user_id):
    db.update_user(user_id, request.form["name"], request.form["email"], request.form["role"], request.form["status"])
    flash("User updated.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def delete_user(user_id):
    if current_user()["id"] == user_id:
        flash("You cannot delete your own admin account.", "warning")
    else:
        db.delete_user(user_id)
        flash("User deleted.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/api/auth/login", methods=["POST"])
def api_login():
    payload = request.get_json(silent=True) or {}
    user = db.get_user_by_email(payload.get("email", "").lower())
    if not user or not check_password_hash(user["password_hash"], payload.get("password", "")):
        return jsonify(error="Invalid credentials"), 401
    return jsonify(access_token=create_access_token(identity=str(user["id"])), user=db.public_user(user))


@app.route("/api/doctors")
def api_doctors():
    return jsonify(doctors=[dict(row) for row in db.list_doctors()])


@app.route("/api/bookings", methods=["GET", "POST"])
@jwt_required()
def api_bookings():
    user = db.get_user(int(get_jwt_identity()))
    if request.method == "GET":
        rows = db.list_bookings(user_id=None if user["role"] == "admin" else user["id"])
        return jsonify(bookings=[dict(row) for row in rows])
    payload = request.get_json(silent=True) or {}
    booking_id = db.create_booking(user["id"], payload["doctor_id"], payload["appointment_date"], payload["appointment_time"], payload.get("reason", ""))
    return jsonify(booking=dict(db.get_booking(booking_id))), 201


if __name__ == "__main__":
    db.init_db()
    app.run(debug=os.getenv("FLASK_DEBUG", "true").lower() == "true")
else:
    db.init_db()
