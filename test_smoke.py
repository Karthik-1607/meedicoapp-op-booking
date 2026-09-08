import os
import tempfile

fd, path = tempfile.mkstemp(suffix='.db'); os.close(fd)
os.environ['DATABASE_PATH'] = path
os.environ['FLASK_DEBUG'] = 'false'
from app import app, db

client = app.test_client()
assert client.get('/').status_code == 200
assert b'Choose your specialist' in client.get('/').data
assert client.post('/register', data={'name':'Test Patient','email':'test@example.com','password':'secret123'}, follow_redirects=True).status_code == 200
login = client.post('/api/auth/login', json={'email':'admin@meedicoapp.local','password':'admin123'})
assert login.status_code == 200
admin_token = login.get_json()['access_token']
assert client.get('/admin').status_code == 302  # browser session is not JWT session
assert client.post('/login', data={'email':'admin@meedicoapp.local','password':'admin123'}).status_code == 302
assert client.get('/admin').status_code == 200
assert client.get('/api/doctors').status_code == 200
patient_login = client.post('/api/auth/login', json={'email':'test@example.com','password':'secret123'})
patient_token = patient_login.get_json()['access_token']
booking = client.post('/api/bookings', headers={'Authorization':f'Bearer {patient_token}'}, json={'doctor_id':1,'appointment_date':'2026-09-12','appointment_time':'10:30','reason':'Routine consultation'})
assert booking.status_code == 201, booking.data
assert client.get('/api/bookings', headers={'Authorization':f'Bearer {patient_token}'}).get_json()['bookings']
print('SMOKE_TEST_PASS')
os.unlink(path)
