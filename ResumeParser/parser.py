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

# Section headers commonly found in resumes
SECTION_PATTERNS = {
    "education": r"(?i)(education|academic background|qualifications|academics)",
    "experience": r"(?i)(experience|work history|employment|professional experience|work experience)",
    "projects": r"(?i)(projects|personal projects|key projects|project experience)",
    "certifications": r"(?i)(certifications|certificates|licenses|credentials)",
    "skills": r"(?i)(skills|technical skills|core competencies|competencies)",
}


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract plain text from a PDF file using pypdf."""
    reader = PdfReader(io.BytesIO(file_bytes))
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n".join(pages)


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract plain text from a DOCX file using python-docx."""
    document = Document(io.BytesIO(file_bytes))
    paragraphs = [para.text for para in document.paragraphs if para.text.strip()]
    return "\n".join(paragraphs)


def extract_text(file_bytes: bytes, filename: str) -> str:
    """Route to the correct extractor based on file extension."""
    name = filename.lower()
    if name.endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)
    if name.endswith(".docx"):
        return extract_text_from_docx(file_bytes)
    raise ValueError("Unsupported file format. Please upload a PDF or DOCX file.")


def extract_email(text: str) -> str:
    """Find the first email address in the resume text."""
    pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    match = re.search(pattern, text)
    return match.group(0) if match else ""


def extract_phone(text: str) -> str:
    """Find a phone number using common formats."""
    patterns = [
        r"\+?\d{1,3}[-.\s]?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}",
        r"\b\d{10}\b",
        r"\(\d{3}\)\s*\d{3}[-.\s]?\d{4}",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0).strip()
    return ""


def extract_full_name(text: str) -> str:
    """
    Guess the candidate name from the first few lines of the resume.
    Skips lines that look like contact info or section headers.
    """
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    skip_pattern = re.compile(
        r"(?i)(resume|curriculum vitae|cv|email|phone|linkedin|github|address|@|http|www\.)"
    )

    for line in lines[:8]:
        if skip_pattern.search(line):
            continue
        # Name is usually short (2-5 words) and mostly alphabetic
        words = line.split()
        if 1 <= len(words) <= 5 and len(line) < 60:
            alpha_ratio = sum(c.isalpha() or c.isspace() for c in line) / max(len(line), 1)
            if alpha_ratio > 0.75:
                return line.title()
    return "Unknown Candidate"


def extract_skills(text: str) -> list[str]:
    """Match known skill keywords against resume text (case-insensitive)."""
    text_lower = text.lower()
    found = []
    for skill in SKILL_KEYWORDS:
        if skill.lower() in text_lower:
            found.append(skill.title() if skill.islower() else skill)
    return sorted(set(found), key=str.lower)


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

    profile = {
        "full_name": extract_full_name(raw_text),
        "email": extract_email(raw_text),
        "phone": extract_phone(raw_text),
        "skills": extract_skills(raw_text),
        "education": _get_section(sections, "education"),
        "experience": _get_section(sections, "experience"),
        "certifications": _get_section(sections, "certifications"),
        "projects": _get_section(sections, "projects"),
        "raw_text": raw_text,
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
