# AI Recruitment & Talent Management Copilot

**Milestone 1: Resume Parser and Candidate Profiling**

A Streamlit-based recruitment dashboard that uploads PDF/DOCX resumes, extracts structured candidate information, and stores profiles in PostgreSQL.

---

## Features

- Clean SaaS-style Streamlit dashboard
- Upload and parse **PDF** and **DOCX** resumes
- Extract: name, email, phone, skills, education, experience, certifications, projects
- Skills displayed as blue badge chips
- Parsing progress metrics (processed count, accuracy, profiles created)
- Recently processed candidates table
- PostgreSQL persistence with graceful offline fallback

---

## Project Structure

```
AI-Recruitment-Talent-Management-Copilot/
└── ResumeParser/
    ├── app.py           # Streamlit dashboard UI
    ├── parser.py        # Resume text extraction and parsing logic
    ├── database.py      # PostgreSQL connection and CRUD operations
    ├── schema.sql       # Database table definition
    ├── requirements.txt # Python dependencies
    └── README.md        # This file
```

---

## Prerequisites

- **Python 3.10+**
- **PostgreSQL 14+** (optional — app works without DB, but won't persist data)

---

## Setup Instructions

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd AI-Recruitment-Talent-Management-Copilot/ResumeParser
```

### 2. Create a virtual environment (recommended)

```bash
# Windows (from repo root)
python -m venv venv
venv\Scripts\activate
cd ResumeParser

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
cd ResumeParser
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up PostgreSQL

#### 4a. Create the database

Open `psql` or pgAdmin and run:

```sql
CREATE DATABASE recruitment_copilot;
```

#### 4b. Create the candidates table

Connect to the new database and run the schema file:

```bash
psql -U postgres -d recruitment_copilot -f schema.sql
```

Or paste the contents of `schema.sql` into pgAdmin's query tool.

#### 4c. Configure connection (optional)

The app uses these defaults:

| Variable      | Default               |
|---------------|-----------------------|
| `DB_HOST`     | `localhost`           |
| `DB_PORT`     | `5432`                |
| `DB_NAME`     | `recruitment_copilot` |
| `DB_USER`     | `postgres`            |
| `DB_PASSWORD` | `postgres`            |

Override them by setting environment variables before running the app:

```bash
# Windows (PowerShell)
$env:DB_HOST = "localhost"
$env:DB_PASSWORD = "your_password"

# macOS / Linux
export DB_HOST=localhost
export DB_PASSWORD=your_password
```

### 5. Run the Streamlit app

```bash
streamlit run app.py
```

The dashboard opens automatically at **http://localhost:8501**.

---

## How It Works

### Parser (`parser.py`)

1. **Text extraction** — `pypdf` for PDF, `python-docx` for DOCX
2. **Email & phone** — Regular expression pattern matching
3. **Full name** — Heuristic from the first lines of the resume
4. **Skills** — Keyword matching against a curated skill list
5. **Sections** — Header-based splitting for education, experience, projects, and certifications

### Database (`database.py`)

- Uses **psycopg v3** for PostgreSQL connectivity
- `save_candidate()` inserts parsed profiles
- `get_recent_candidates()` powers the dashboard table
- If the database is unreachable, the app shows a warning and still displays parsed data

### UI (`app.py`)

- Left sidebar with navigation (Dashboard, Resume Upload, Candidates, etc.)
- Upload card, parsing progress card, profile card, and candidates table
- Custom CSS: light gray background, white cards, blue accent, rounded corners

---

## Usage

1. Open the app in your browser
2. Click **Resume Upload** in the sidebar (default view)
3. Upload a `.pdf` or `.docx` resume
4. Click **Parse Resume**
5. Review the extracted profile and skills badges
6. Check the **Recently Processed Candidates** table

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `Database offline` warning | Start PostgreSQL and verify credentials |
| Empty skills list | Resume may use uncommon skill names; add keywords in `parser.py` |
| Name shows "Unknown Candidate" | Ensure the name is on the first few lines of the resume |
| PDF text is garbled | Some scanned PDFs need OCR (not included in Milestone 1) |

---

## Tech Stack

| Component | Library |
|-----------|---------|
| UI | Streamlit |
| PDF parsing | pypdf |
| DOCX parsing | python-docx |
| Database | PostgreSQL |
| DB driver | psycopg |

---

## License

MIT — free to use for academic and personal projects.
