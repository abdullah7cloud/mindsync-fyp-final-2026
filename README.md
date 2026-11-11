# MindSync

**MindSync is a web app that helps university students plan their study and avoid burnout.**
It was made as a Final Year Project (CTEC3451) at De Montfort University (delivered through Niels Brock, Copenhagen).

The student writes what they must study and by when. MindSync makes a day-by-day study plan. The plan is built to fit the student's energy and mood, so the student does not study too much in one day.

> This project is a study tool. It is **not** a medical or mental-health tool. It does not diagnose anything.

---

## What the website does

The website has six pages:

| Page | What it does |
|---|---|
| Dashboard | Shows the student's real progress and the next tasks. |
| Study Planner | The student adds a subject, a deadline and some notes. MindSync makes a roadmap with small daily tasks. |
| AI Learning Zone | Makes quiz questions and flashcards from the student's own notes. |
| My Notebook | A place to keep notes and documents. |
| My Profile | Name, picture, change e-mail (with a 6-digit code) and password. |
| Settings | Light or dark theme, e-mail reminders, time zone. |

### How the study plan is made

1. **Google Gemini** (an AI) writes the roadmap and the tasks.
2. **MindSync checks the answer** with its own rules (for example: not too many minutes in one day, nothing past the deadline).
3. If Gemini is **slow, switched off, or there is no internet**, MindSync uses its own **built-in planner**. The student still gets a plan. The page says which one made it.

The student's mood and stress answers are **never sent to Gemini**. They are only used on the computer to limit how much work is planned per day.

### E-mail reminders

MindSync sends an e-mail when about 30% or 35% of the time before a deadline is left (the student chooses in Settings). If no mail server is set up, the e-mails are saved as files in `backend/outbox` instead (this folder is not uploaded to GitHub).

---

## Technologies

| Part | Technology |
|---|---|
| Website (frontend) | React and Vite |
| Server (backend) | Python and FastAPI |
| Database | PostgreSQL (tests can also use SQLite) |
| Login | JWT tokens, passwords saved with Argon2id |
| AI | Google Gemini (optional, free key) |
| E-mail | Gmail (App Password) or any SMTP server |

---

## Folder map

```
MindSync/
  backend/        the server (Python / FastAPI)
    app/          the program code
    tests/        automatic tests
    scripts/      helper and test scripts
    ml_training/  how the small stress model was trained
    .env.example  a blank settings file (copy it to .env)
  frontend/       the website (React)
    src/          the page code
    public/       pictures
  database/       schema.sql - the list of database tables
  docs/           guides, test results, diagrams
  e2e/            browser tests
  START-MINDSYNC.bat    one-click start on Windows
  README.md       this file
```

---

## What you need first

1. **Python** 3.11 or newer (I used 3.14 on Windows) - https://www.python.org
2. **Node.js** 18 or newer (includes npm) - https://nodejs.org
3. **PostgreSQL** (with pgAdmin) - https://www.postgresql.org
4. *(Optional)* A free **Gemini API key** from Google AI Studio.
5. *(Optional)* A **Gmail App Password** for real e-mail reminders.

---

## Install and run (Windows)

### Step 1 - Make an empty database

Open pgAdmin, right-click **Databases**, choose **Create > Database**, and call it `mindsync`.
You do not need to make the tables. MindSync makes them by itself when it starts. (The list of tables is in `database/schema.sql` if you want to read it.)

### Step 2 - Easy way: double-click `START-MINDSYNC.bat`

The first time, it asks for your PostgreSQL password and makes `backend\.env` for you. Then it installs what is needed, starts the backend and the website, and opens the browser.

### Step 2 (other way) - Start by hand

**Backend** (first window):

```
cd backend
copy .env.example .env
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app
```

Open `backend\.env` in Notepad and set at least `DATABASE_URL` (your PostgreSQL password) and `JWT_SECRET` (any long random text).
You can make a good secret with:

```
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

**Website** (second window):

```
cd frontend
copy .env.example .env
npm install
npm run dev
```

### Step 3 - Open the website

Go to **http://localhost:5173** (type `localhost`, not `127.0.0.1`).
The backend runs at http://localhost:8000. Its API pages are at http://localhost:8000/docs.

---

## Optional: switch on Gemini (the AI)

Open `backend\.env` and set:

```
AI_PROVIDER=gemini
GEMINI_API_KEY=<paste your own key here>
GEMINI_MODEL=gemini-3.5-flash-lite
```

Restart the backend. Without a key, MindSync still works and uses the built-in planner.
Read `docs/AI_ACTIVATION_GUIDE.md` for more. Note: Google may use free-plan content to improve its products, so do not type private information.

## Optional: switch on real e-mail reminders

In `backend\.env` set `SMTP_HOST=smtp.gmail.com`, `SMTP_PORT=587`, `SMTP_USER`, `SMTP_PASSWORD` (a Gmail **App Password**, not your normal password) and `SMTP_FROM`. See `docs/UPDATE_28_GUIDE.md` and `docs/EMAIL_ALERTS.md`.

---

## Run the tests

Backend (from the `backend` folder, with the virtual environment active):

```
python -m pytest -q
```

Website (from the `frontend` folder):

```
npm test
```

Browser, security and speed tests are in `e2e/` and `backend/scripts/`. The `run-*.bat` files in the main folder start them. Results are written up in `docs/` (for example `docs/security_test_results.md` and `docs/latency_results.md`).

---

## Security

- Passwords are saved with **Argon2id**. Login uses **JWT** tokens.
- All inputs are checked by schemas (Pydantic). Database rules are in `database/schema.sql`.
- Student text that goes to the AI is cleaned and marked as data, to defend against prompt injection. AI answers are checked before they are shown.
- There are limits on AI use per student and per month.
- **Secrets are never stored in this repository.** The files `backend/.env` and `frontend/.env` are in `.gitignore`. Only the blank `.env.example` files are uploaded.

## Known limits

- The free Gemini plan has limits and can be slow sometimes. The built-in planner then takes over.
- The stress model is trained on a public student dataset. In that dataset the stress score is a fixed formula, so the model only learns that formula. It is not a medical tool. Details: `docs/WELLBEING_MODEL.md` and `docs/KNOWN_LIMITATIONS.md`.
- A real user study (usability test) has not been done.
- The training dataset is not included. See `docs/WELLBEING_MODEL.md` for where to get it.

---

## Author

Muhammad Abdullah - Final Year Project, CTEC3451.
Supervisor: Syed Muhammad Ali.
Academic project, 2026. Photos are free-licence (see `docs/IMAGE_CREDITS.md`).
