"""
Resume Parser Module
--------------------
Extracts structured candidate information from PDF and DOCX resume files.
Uses regex, keyword matching, and section-based parsing.
"""

import io
import re
from typing import Any

from docx import Document
from pypdf import PdfReader

# Common technical and soft skills for keyword matching
SKILL_KEYWORDS = [
    "python", "java", "javascript", "typescript", "c++", "c#", "ruby", "go", "rust",
    "sql", "html", "css", "react", "angular", "vue", "node.js", "django", "flask",
    "fastapi", "spring", "docker", "kubernetes", "aws", "azure", "gcp", "git",
    "machine learning", "deep learning", "data analysis", "data science", "pandas",
    "numpy", "tensorflow", "pytorch", "scikit-learn", "nlp", "computer vision",
    "postgresql", "mysql", "mongodb", "redis", "rest api", "graphql", "microservices",
    "agile", "scrum", "project management", "leadership", "communication",
    "problem solving", "teamwork", "excel", "power bi", "tableau", "linux",
    "ci/cd", "jenkins", "terraform", "ansible", "figma", "photoshop",
    "streamlit", "selenium", "junit", "pytest", "unit testing",
]

SKILL_NORMALIZATION = {
    "node.js": "Node.js",
    "rest api": "REST API",
    "restapi": "REST API",
    "graphql": "GraphQL",
    "aws": "AWS",
    "gcp": "GCP",
    "azure": "Azure",
    "ci/cd": "CI/CD",
    "nlp": "NLP",
    "ml": "ML",
    "ai": "AI",
    "python": "Python",
    "java": "Java",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "c#": "C#",
    "c++": "C++",
    "html": "HTML",
    "css": "CSS",
    "react": "React",
    "angular": "Angular",
    "vue": "Vue",
    "django": "Django",
    "flask": "Flask",
    "fastapi": "FastAPI",
    "spring": "Spring",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "postgresql": "PostgreSQL",
    "mysql": "MySQL",
    "mongodb": "MongoDB",
    "redis": "Redis",
    "pandas": "Pandas",
    "numpy": "NumPy",
    "tensorflow": "TensorFlow",
    "pytorch": "PyTorch",
    "scikit-learn": "Scikit-Learn",
    "power bi": "Power BI",
    "tableau": "Tableau",
    "streamlit": "Streamlit",
    "selenium": "Selenium",
    "junit": "JUnit",
    "pytest": "Pytest",
    "excel": "Excel",
    "terraform": "Terraform",
    "ansible": "Ansible",
    "figma": "Figma",
    "photoshop": "Photoshop",
}

# Section headers commonly found in resumes
SECTION_PATTERNS = {
    "education": r"(?i)(education|academic background|qualifications|academics)",
    "experience": r"(?i)(experience|work history|employment|professional experience|work experience)",
    "projects": r"(?i)(projects|personal projects|key projects|project experience)",
    "certifications": r"(?i)(certifications|certificates|licenses|credentials)",
    "skills": r"(?i)(skills|technical skills|core competencies|competencies)",
}

# Lines that must never be treated as a person's name
SECTION_HEADINGS = {
    "professional summary",
    "summary",
    "objective",
    "career objective",
    "profile",
    "about me",
    "skills",
    "technical skills",
    "core competencies",
    "competencies",
    "education",
    "experience",
    "work experience",
    "professional experience",
    "work history",
    "employment",
    "projects",
    "personal projects",
    "certifications",
    "certificates",
    "licenses",
    "contact",
    "contact information",
    "references",
    "achievements",
    "curriculum vitae",
    "resume",
    "cv",
}


def normalize_extracted_text(text: str) -> str:
    text = text.replace("\xa0", " ").replace("\u200b", " ")
    text = re.sub(r"\s*@\s*", "@", text)
    text = re.sub(r"\s*\.\s*", ".", text)
    text = re.sub(r"[ \t\f\v]+", " ", text)
    text = re.sub(r"[ ]{2,}", " ", text)
    text = re.sub(r"\r\n|\r", "\n", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def extract_pdf_text(file_bytes: bytes) -> str:
    """Extract plain text from a PDF file using pypdf."""
    file = io.BytesIO(file_bytes)
    file.seek(0)
    reader = PdfReader(file)
    pages = []
    for page in reader.pages:
        page_text = page.extract_text()
        pages.append(page_text or "")
    raw_text = "\n".join(pages)
    return normalize_extracted_text(raw_text)


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract plain text from a DOCX file using python-docx."""
    document = Document(io.BytesIO(file_bytes))
    paragraphs = [para.text for para in document.paragraphs if para.text.strip()]
    return normalize_extracted_text("\n".join(paragraphs))


def extract_text(file_bytes: bytes, filename: str) -> str:
    """Route to the correct extractor based on file extension."""
    name = filename.lower()
    if name.endswith(".pdf"):
        return extract_pdf_text(file_bytes)
    if name.endswith(".docx"):
        return extract_text_from_docx(file_bytes)
    raise ValueError("Unsupported file format. Please upload a PDF or DOCX file.")


def extract_email(text: str) -> str:
    """Find the first email address in the resume text."""
    search_text = text.replace("\xa0", " ")
    search_text = re.sub(r"\s*@\s*", "@", search_text)
    search_text = re.sub(r"\s*\.\s*", ".", search_text)
    pattern = r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[A-Za-z]{2,}"
    match = re.search(pattern, search_text)
    return match.group(0) if match else ""


def extract_phone(text: str) -> str:
    """Find a phone number using common formats."""
    search_text = text.replace("\xa0", " ").replace("\u200b", " ")
    patterns = [
        r"(?:\+91[\s\-]?)?\d{5}[\s\-]?\d{5}",
        r"(?:\+?\d{1,3}[\s\-]?)?\(?\d{2,4}\)?[\s\-]?\d{3,4}[\s\-]?\d{3,4}",
        r"\b\d{10}\b",
        r"\b\d{3}[\s\-]\d{3}[\s\-]\d{4}\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, search_text)
        if match:
            return re.sub(r"\s+", " ", match.group(0)).strip()
    return ""


def _is_section_heading(line: str) -> bool:
    """Return True if the line is a resume section title, not a person name."""
    cleaned = re.sub(r'^[•\-\*■❑\d\.\s\)\(]+', '', line)  # Remove list bullets, numbers
    normalized = cleaned.strip().lower().rstrip(":").strip()
    if not normalized:
        return True
    if normalized in SECTION_HEADINGS:
        return True
    for heading in SECTION_HEADINGS:
        if normalized == heading or normalized.startswith(heading + " ") or normalized.startswith(heading + ":"):
            return True
    return False


def _name_from_filename(filename: str) -> str:
    """Derive a readable name from the uploaded file name."""
    import os

    base = os.path.splitext(os.path.basename(filename))[0]
    base = re.sub(r"([a-z])([A-Z])", r"\1 \2", base)  # Split camel/PascalCase
    base = re.sub(r"[_\-]+", " ", base)
    cleaned = re.sub(r"(?i)\b(resume|cv|pdf|docx|profile|updated|latest|new|copy)\b", "", base)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned.title() if cleaned else "Unknown Candidate"


def extract_full_name(text: str, filename: str = "") -> str:
    """
    Extract the candidate name from resume text.
    Priority: Name:/Full Name: label → first valid line → cleaned file name.
    """
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    # 1. Check for "Name:" or "Full Name:" first in the first 12 lines.
    for idx, line in enumerate(lines[:12]):
        m = re.match(r"(?i)^\s*(?:full\s+name|name)\s*[:\-]\s*(.*)", line)
        if m:
            candidate = m.group(1).strip()
            if not candidate and idx + 1 < len(lines):
                candidate = lines[idx + 1].strip()
            if candidate and not _is_section_heading(candidate) and "@" not in candidate:
                if len(candidate) < 60:
                    return candidate.title()

    # 2. Iterate lines to find first line that looks like a name (restricted to first 3 lines)
    skip_pattern = re.compile(
        r"(?i)(resume|curriculum vitae|cv|email|phone|linkedin|github|address|@|http|www\.)"
    )
    for line in lines[:3]:
        if skip_pattern.search(line):
            continue
        if _is_section_heading(line):
            continue
        words = line.split()
        if 1 <= len(words) <= 5 and len(line) < 60:
            alpha_ratio = sum(c.isalpha() or c.isspace() for c in line) / max(len(line), 1)
            if alpha_ratio > 0.75:
                # Ensure no digits or symbols that don't belong in a name
                if not any(c.isdigit() or c in "@#$^*+=_[]{}|\\<>/~`!?" for c in line):
                    return line.title()

    if filename:
        return _name_from_filename(filename)
    return "Unknown Candidate"


def normalize_skill_name(skill: str) -> str:
    """Normalize skill names for consistent aggregation and display."""
    if not skill:
        return ""
    candidate = skill.strip()
    normalized_key = re.sub(r"[^\w\+#\.\- ]+", "", candidate.lower()).strip()
    if normalized_key in SKILL_NORMALIZATION:
        return SKILL_NORMALIZATION[normalized_key]
    if candidate.isupper() and len(candidate) <= 5:
        return candidate
    if normalized_key in {"ai", "ml", "nlp", "sql", "aws", "gcp", "ci/cd"}:
        return normalized_key.upper()
    return candidate.title()


def normalize_skills_list(skills: list[str]) -> list[str]:
    normalized = []
    seen = set()
    for skill in skills:
        cleaned = normalize_skill_name(skill)
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            normalized.append(cleaned)
    return sorted(normalized, key=str.lower)


def extract_skills(text: str) -> list[str]:
    """Match known skill keywords against resume text (case-insensitive)."""
    text_lower = text.lower()
    found = []
    for skill in SKILL_KEYWORDS:
        if skill.lower() in text_lower:
            found.append(normalize_skill_name(skill))
    return normalize_skills_list(found)


def _split_into_sections(text: str) -> dict[str, str]:
    """
    Split resume text into sections based on common header keywords.
    Returns a dict mapping section name to its content.
    """
    lines = text.split("\n")
    sections: dict[str, list[str]] = {}
    current_section = "header"
    sections[current_section] = []

    header_regex = {key: re.compile(pattern) for key, pattern in SECTION_PATTERNS.items()}

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        matched_section = None
        for section_name, regex in header_regex.items():
            if regex.fullmatch(stripped) or regex.match(stripped):
                matched_section = section_name
                break

        if matched_section:
            current_section = matched_section
            sections.setdefault(current_section, [])
        else:
            sections.setdefault(current_section, []).append(stripped)

    return {key: "\n".join(value).strip() for key, value in sections.items()}


def _get_section(sections: dict[str, str], *names: str) -> str:
    """Return the first matching section content, or empty string."""
    for name in names:
        content = sections.get(name, "")
        if content:
            return content
    return ""


def parse_resume(file_bytes: bytes, filename: str) -> dict[str, Any]:
    """
    Main parsing function.
    Returns a dictionary with all extracted candidate fields.
    """
    raw_text = extract_text(file_bytes, filename)
    sections = _split_into_sections(raw_text)
    file_type = "pdf" if filename.lower().endswith(".pdf") else "docx"

    profile = {
        "full_name": extract_full_name(raw_text, filename),
        "email": extract_email(raw_text),
        "phone": extract_phone(raw_text),
        "skills": extract_skills(raw_text),
        "education": _get_section(sections, "education"),
        "experience": _get_section(sections, "experience"),
        "certifications": _get_section(sections, "certifications"),
        "projects": _get_section(sections, "projects"),
        "raw_text": raw_text,
        "source_filename": filename,
        "source_file_type": file_type,
    }

    # If skills section exists but keyword matching found little, include section text
    skills_section = _get_section(sections, "skills")
    if skills_section and len(profile["skills"]) < 3:
        # Pull comma/pipe separated skills from the skills section
        extra = re.split(r"[,|•\n;]", skills_section)
        for item in extra:
            cleaned = item.strip()
            if cleaned and len(cleaned) < 40:
                profile["skills"].append(cleaned)
        profile["skills"] = sorted(set(profile["skills"]), key=str.lower)

    return profile


def calculate_extraction_accuracy(profile: dict[str, Any]) -> float:
    """
    Estimate how complete the extracted profile is (0–100%).
    Used for the dashboard progress metrics.
    """
    fields = ["full_name", "email", "phone", "education", "experience", "skills"]
    filled = 0
    for field in fields:
        value = profile.get(field)
        if field == "full_name" and value == "Unknown Candidate":
            continue
        if value:
            filled += 1
    return round((filled / len(fields)) * 100, 1)
