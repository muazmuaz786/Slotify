# Slotify API

Django REST API for managing services, bookings, time slots, reviews/comments, and ratings.

## Stack
- Python 3.13+
- Django 6.0
- Django REST Framework
- JWT auth via `djangorestframework-simplejwt`

## Quick start
```bash
python -m venv .venv
. .venv/Scripts/activate        # PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

# env file (copy and adjust)
copy .env.example .env   # then edit SECRET_KEY, ALLOWED_HOSTS, DATABASE_URL, CACHE_URL as needed

# run migrations
python manage.py migrate

# create superuser
python manage.py createsuperuser

# start dev server
python manage.py runserver
```

## Useful endpoints (router-based)
- `/user/` users & auth actions (`login`, `refresh`, `logout`, `follow`, `unfollow`)
- `/service/` services
- `/booking/` bookings + `booking/check-slot/`
- `/slot/` slots
- `/rate/` ratings
- `/review/` reviews
- `/comment/` comments

## Caching
- Slot availability and average ratings cached (locmem by default). Replace `CACHES` in `Slotify/settings.py` to use Redis/Memcached in production.

## JWT cookies
Login returns tokens and also sets HttpOnly cookies (`access`, `refresh`). Adjust cookie security flags for production.

## Git/GitHub workflow (from project root `Backend/Django/Slotify`)
```bash
git init
git add .
git commit -m "Initial Slotify API"
# create repo on GitHub named Slotify (or any)
git branch -M main
git remote add origin https://github.com/<your-username>/<repo>.git
git push -u origin main
```

## Notes
- Secrets are in `.env`; keep them out of commits.
- Media files are served in DEBUG via `urls.py`; configure your web server for production.
