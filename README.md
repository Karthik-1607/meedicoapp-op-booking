# Meedicoapp OP-Booking System

A full-stack Flask application for outpatient appointment booking, built with SQLite, explicit SQL cursors, Bootstrap 5, role-based administration, JWT APIs, CORS, and configurable email notifications.

## Features

- Patient registration, login, appointment booking, and booking history.
- Seeded doctor directory with specialty, availability, experience, and consultation fee.
- Role-based admin dashboard with patient/doctor/booking metrics.
- Admin user update and delete management with role and status controls.
- JSON API authentication with JWT and protected booking endpoints.
- CORS enabled for `/api/*` and Flask-Mail confirmation emails.
- SQLite schema creation and seed data on first startup.

## Quick start

```bash
cd /home/ubuntu/meedicoapp_op_booking
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`. The development admin account is `admin@meedicoapp.local` / `admin123`; change it before production use.

## Run directly from GitHub without downloading files

The repository includes `render.yaml` for deployment on Render. Go to [render.com](https://render.com), sign in with GitHub, choose **New → Blueprint**, select `Karthik-1607/meedicoapp-op-booking`, and click **Apply**. Render will install the dependencies, start Gunicorn, and provide a public HTTPS URL. Open that URL to use the homepage, registration, login, booking flow, and admin dashboard. The first deployment may take a few minutes.

The included SQLite database is suitable for a demo or evaluation deployment. For production, use a managed database because free web-service filesystems may not persist SQLite data across redeploys.

Optional mail settings can be provided with `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_TLS`, `MAIL_USERNAME`, `MAIL_PASSWORD`, and `MAIL_DEFAULT_SENDER`. Set `SECRET_KEY`, `JWT_SECRET_KEY`, and `DATABASE_PATH` in the deployment environment.

## API

`POST /api/auth/login` accepts `{ "email": "...", "password": "..." }` and returns a JWT. Send it as `Authorization: Bearer <token>` to `GET /api/doctors`, `GET /api/bookings`, or `POST /api/bookings`.

Example booking payload:

```json
{"doctor_id": 1, "appointment_date": "2026-09-12", "appointment_time": "10:30", "reason": "Routine consultation"}
```

This starter is suitable for local development. For production, add CSRF protection for browser forms, rotate secrets, use HTTPS, configure a production WSGI server, and apply stronger validation and audit logging.

## Test every page and flow

Start the server with `python app.py`, then run `python test_pages.py`. The browser test uses Chromium to render the homepage, login page, registration page, authenticated patient homepage, booking confirmation, and admin dashboard. It also exercises patient registration, patient login, appointment booking, and admin login. Screenshots are written to the local `preview/` directory and intentionally excluded from Git.
