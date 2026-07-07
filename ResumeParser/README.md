# AI Recruitment & Talent Management Copilot

**Milestone 1: Resume Parser and Candidate Profiling**

A Streamlit-based recruitment dashboard that uploads PDF/DOCX resumes, extracts structured candidate information, and stores profiles in MongoDB.

---

## Features

- Clean SaaS-style Streamlit dashboard
- Upload and parse **PDF** and **DOCX** resumes
- Extract: name, email, phone, skills, education, experience, certifications, projects
- Skills displayed as blue badge chips
- Parsing progress metrics (processed count, accuracy, profiles created)
- Recently processed candidates table
- MongoDB persistence with graceful offline fallback

---

## Project Structure

```
AI-Recruitment-Talent-Management-Copilot/
└── ResumeParser/
    ├── app.py           # Streamlit dashboard UI
    ├── parser.py        # Resume text extraction and parsing logic
    ├── database.py      # MongoDB connection and CRUD operations
    ├── schema.sql.old   # Legacy database table definition (PostgreSQL reference)
    ├── requirements.txt # Python dependencies
    └── README.md        # This file
```

---

## Prerequisites

- **Python 3.10+**
- **MongoDB 5.0+** (optional — app works without DB, but won't persist data)

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

### 4. Set up MongoDB

#### 4a. Setup local or remote MongoDB instance

The application can connect to a local MongoDB server (`mongodb://localhost:27017/`) or a remote MongoDB Atlas database cluster.

#### 4b. Configure environment variables (`.env` file)

Create a `.env` file inside the `ResumeParser` directory (if it doesn't already exist) with the following connection details:

```env
MONGO_URI=mongodb://localhost:27017/
MONGO_DB=recruitment_copilot
MONGO_COLLECTION=candidates
```

Replace `MONGO_URI` with your connection string if you are using MongoDB Atlas or running on a non-standard port.

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

- Uses **pymongo** for MongoDB connectivity
- `save_candidate()` checks for duplicate candidates by email/phone and inserts unique profiles
- `get_all_candidates()` queries all candidate profiles with search filters
- `get_recent_candidates()` fetches the latest candidate entries for the dashboard
- If the database is unreachable, the app shows a warning and still displays parsed data offline

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
| `Database offline` warning | Start MongoDB and verify the credentials in the `.env` file |
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
| Database | MongoDB |
| DB driver | pymongo |

---

## License

MIT — free to use for academic and personal projects.
