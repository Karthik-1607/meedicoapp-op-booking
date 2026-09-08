import os
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = os.getenv('APP_URL', 'http://127.0.0.1:5000')
OUT = Path('preview')
OUT.mkdir(exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox'])
    page = browser.new_page(viewport={'width': 1440, 'height': 1000}, device_scale_factor=1)
    checks = []

    def visit(path, name, expected):
        response = page.goto(BASE + path, wait_until='networkidle')
        body = page.locator('body').inner_text()
        assert response and response.status == 200, f'{path}: HTTP {response.status if response else None}'
        assert expected in body, f'{path}: missing {expected!r}'
        page.screenshot(path=str(OUT / f'{name}.png'), full_page=True)
        checks.append(f'{name}: HTTP {response.status}')

    visit('/', '01-homepage', 'Choose your specialist')
    visit('/login', '02-login', 'Welcome back')
    visit('/register', '03-register', 'Create your account')

    page.goto(BASE + '/register', wait_until='networkidle')
    page.fill('input[name="name"]', 'Preview Patient')
    page.fill('input[name="email"]', 'preview.patient@example.com')
    page.fill('input[name="password"]', 'secret123')
    page.locator('form button').click()
    page.wait_for_load_state('networkidle')
    assert '/login' in page.url
    checks.append('register flow: passed')

    page.fill('input[name="email"]', 'preview.patient@example.com')
    page.fill('input[name="password"]', 'secret123')
    page.locator('form button').click()
    page.wait_for_load_state('networkidle')
    assert page.url.endswith('/')
    page.screenshot(path=str(OUT / '04-patient-homepage.png'), full_page=True)
    checks.append('patient login flow: passed')

    page.click('button:has-text("Book appointment")')
    page.fill('input[name="appointment_date"]', '2026-09-20')
    page.fill('input[name="appointment_time"]', '10:30')
    page.fill('textarea[name="reason"]', 'Preview consultation')
    page.click('.modal button[type="submit"]')
    page.wait_for_load_state('networkidle')
    assert 'Appointment confirmed' in page.locator('body').inner_text()
    page.screenshot(path=str(OUT / '05-booking-confirmed.png'), full_page=True)
    checks.append('booking flow: passed')

    page.goto(BASE + '/login', wait_until='networkidle')
    page.fill('input[name="email"]', 'admin@meedicoapp.local')
    page.fill('input[name="password"]', 'admin123')
    page.locator('form button').click()
    page.wait_for_load_state('networkidle')
    assert '/admin' in page.url
    assert 'Admin dashboard' in page.locator('body').inner_text()
    page.screenshot(path=str(OUT / '06-admin-dashboard.png'), full_page=True)
    checks.append('admin login/dashboard flow: passed')

    browser.close()

print('\n'.join(checks))
print(f'captured screenshots: {len(list(OUT.glob("*.png")))}')
