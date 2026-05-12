# Feedback UI — Flask + SQLite

A full-stack feedback collection app with an admin panel.

## Quick Start

```bash
# 1. Install dependencies
pip install flask werkzeug

# 2. Run the app
python app.py
```

Server starts at **http://localhost:5000**

---

## Default Admin Credentials
| Field    | Value      |
|----------|------------|
| Username | `admin`    |
| Password | `admin123` |

> Change these after first login by editing the DB or adding a change-password route.

---

## Routes

| Method | URL                     | Description                   |
|--------|-------------------------|-------------------------------|
| GET    | `/`                     | Public feedback form           |
| POST   | `/submit`               | Submit a review                |
| GET    | `/admin/login`          | Admin login page               |
| POST   | `/admin/login`          | Authenticate admin             |
| GET    | `/admin/logout`         | Log out                        |
| GET    | `/admin/dashboard`      | View all reviews (protected)   |
| POST   | `/admin/delete/<id>`    | Delete a review (protected)    |
| GET    | `/admin/export`         | Download reviews as CSV        |

---

## Project Structure

```
feedback-app/
├── app.py                  # Flask app + all routes
├── requirements.txt
├── instance/
│   └── feedback.db         # SQLite database (auto-created)
├── templates/
│   ├── base.html
│   ├── index.html          # Public feedback form
│   └── admin/
│       ├── login.html
│       └── dashboard.html
└── static/
    ├── css/
    │   ├── main.css        # Shared styles
    │   └── admin.css       # Dashboard styles
    └── js/
        └── feedback.js     # Form interactivity
```

---

## Features
- Emoji-based rating (Unhappy / Neutral / Satisfied / Love it!)
- Name + email collection with server-side validation
- SQLite storage via Python's built-in `sqlite3`
- Session-based admin login with password hashing (Werkzeug)
- Admin dashboard with search, filter by rating, sort, pagination
- One-click CSV export
- Delete individual reviews
- Fully responsive dark UI

## Production Notes
- Set `SECRET_KEY` as an environment variable
- Use a WSGI server (gunicorn): `gunicorn app:app`
- Consider adding rate limiting on `/submit`
