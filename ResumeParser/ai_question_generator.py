"""
AI Interview Question Generator Module using Groq API
------------------------------------------------------
Generates category-grouped (Technical, Behavioural, Situational, Follow-up)
interview questions based on candidate profile, resume, projects, experience,
and job description requirements.
"""

import json
import os
import requests
from typing import Any


def call_groq_api(prompt: str, api_key: str | None = None, model: str = "llama-3.3-70b-versatile") -> str:
    """
    Sends chat request to Groq API endpoint.
    """
    key = api_key or os.getenv("GROQ_API_KEY") or os.getenv("GROQ_KEY", "")
    if not key or not key.strip():
        raise ValueError("Groq API key not provided. Set GROQ_API_KEY environment variable or provide key in settings.")

    headers = {
        "Authorization": f"Bearer {key.strip()}",
        "Content-Type": "application/json",
    }

    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an expert technical recruiter and AI hiring specialist. "
                    "Your task is to generate precise, structured interview questions in JSON format. "
                    "Always respond ONLY with a valid JSON object adhering strictly to the requested schema, without markdown formatting around the JSON."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.5,
        "max_tokens": 2500,
    }

    response = requests.post(url, headers=headers, json=payload, timeout=25)
    if response.status_code != 200:
        raise RuntimeError(f"Groq API Error ({response.status_code}): {response.text}")

    data = response.json()
    try:
        content = data["choices"][0]["message"]["content"].strip()
        # Clean markdown codeblocks if model wrapped output
        if content.startswith("```"):
            lines = content.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            content = "\n".join(lines).strip()
        return content
    except (KeyError, IndexError) as err:
        raise RuntimeError(f"Unexpected response structure from Groq API: {err}")


def generate_interview_questions_ai(
    candidate: dict[str, Any],
    job: dict[str, Any],
    difficulty: str = "Mixed",
    num_questions: int = 10,
    groq_api_key: str | None = None,
) -> list[dict[str, str]]:
    """
    Generates structured interview questions categorized into Technical, Behavioural, Situational, and Follow-up.
    Each question dict contains: question, category, difficulty, expected_skill.
    """
    c_name = candidate.get("full_name", "Candidate")
    c_skills = candidate.get("skills", [])
    if isinstance(c_skills, list):
        c_skills_str = ", ".join([str(s) for s in c_skills])
    else:
        c_skills_str = str(c_skills or "Not specified")

    c_projects = str(candidate.get("projects", "Not specified"))
    c_experience = str(candidate.get("experience", "Not specified"))
    c_raw = str(candidate.get("raw_text", ""))[:1500]

    j_title = job.get("job_title", "Position")
    j_skills = job.get("required_skills", [])
    if isinstance(j_skills, list):
        j_skills_str = ", ".join([str(s) for s in j_skills])
    else:
        j_skills_str = str(j_skills or "Not specified")

    j_resp = str(job.get("responsibilities", job.get("job_description", "Not specified")))[:1000]

    prompt = f"""
Generate exactly {num_questions} interview questions for candidate '{c_name}' applying for job role '{j_title}'.

Target Difficulty: {difficulty}

Candidate Background:
- Technical Skills: {c_skills_str}
- Notable Projects: {c_projects}
- Past Experience: {c_experience}
- Resume Snippet: {c_raw}

Job Vacancy Details:
- Target Job Title: {j_title}
- Required Job Skills: {j_skills_str}
- Key Responsibilities: {j_resp}

Categorize questions into these 4 categories:
1. Technical (Test specific required job skills)
2. Behavioural (Assess communication, teamwork, conflict resolution)
3. Situational (Real-world scenarios related to job responsibilities)
4. Follow-up (Tailored specifically to the candidate's listed skills, past experience, and projects)

Required Output JSON Schema:
{{
  "questions": [
    {{
      "question": "Full clear text of the question",
      "category": "Technical" | "Behavioural" | "Situational" | "Follow-up",
      "difficulty": "Beginner" | "Intermediate" | "Advanced",
      "expected_skill": "Primary skill or competency evaluated"
    }}
  ]
}}

Return raw valid JSON only. Do not add conversational text.
"""

    try:
        raw_json_str = call_groq_api(prompt, api_key=groq_api_key)
        parsed = json.loads(raw_json_str)
        questions = parsed.get("questions", [])
        if isinstance(questions, list) and len(questions) > 0:
            return sanitize_questions(questions, difficulty)
    except Exception as exc:
        print(f"[Warning] Groq API question generation failed ({exc}). Falling back to heuristic question engine.")

    # Heuristic Fallback Question Engine
    return fallback_generate_questions(candidate, job, difficulty, num_questions)


def regenerate_single_question_ai(
    category: str,
    target_difficulty: str,
    expected_skill: str,
    candidate: dict[str, Any],
    job: dict[str, Any],
    groq_api_key: str | None = None,
) -> dict[str, str]:
    """
    Regenerates a single interview question via Groq API.
    """
    c_name = candidate.get("full_name", "Candidate")
    j_title = job.get("job_title", "Position")

    prompt = f"""
Generate ONE single unique {category} interview question for candidate '{c_name}' for job role '{j_title}'.
Category: {category}
Difficulty: {target_difficulty}
Expected Skill: {expected_skill}

Output JSON schema:
{{
  "question": "Question text",
  "category": "{category}",
  "difficulty": "{target_difficulty}",
  "expected_skill": "{expected_skill}"
}}
Return raw valid JSON only.
"""
    try:
        raw_json_str = call_groq_api(prompt, api_key=groq_api_key)
        parsed = json.loads(raw_json_str)
        if isinstance(parsed, dict) and "question" in parsed:
            return {
                "question": str(parsed.get("question", "")),
                "category": category,
                "difficulty": target_difficulty,
                "expected_skill": str(parsed.get("expected_skill", expected_skill)),
            }
    except Exception:
        pass

    # Heuristic Fallback
    return {
        "question": f"Describe a practical scenario where you demonstrated excellence in {expected_skill} for a {j_title} role.",
        "category": category,
        "difficulty": target_difficulty,
        "expected_skill": expected_skill,
    }


def sanitize_questions(questions: list[dict], global_diff: str) -> list[dict[str, str]]:
    valid_categories = ["Technical", "Behavioural", "Situational", "Follow-up"]
    valid_difficulties = ["Beginner", "Intermediate", "Advanced"]
    clean = []

    for q in questions:
        cat = q.get("category", "Technical").capitalize()
        if cat not in valid_categories:
            cat = "Technical"

        diff = q.get("difficulty", "Intermediate").capitalize()
        if diff not in valid_difficulties:
            diff = "Intermediate" if global_diff == "Mixed" else global_diff

        skill = str(q.get("expected_skill", "General Competency")).strip()
        q_text = str(q.get("question", "")).strip()

        if q_text:
            clean.append({
                "question": q_text,
                "category": cat,
                "difficulty": diff,
                "expected_skill": skill if skill else "General Competency",
            })
    return clean


def fallback_generate_questions(
    candidate: dict[str, Any],
    job: dict[str, Any],
    difficulty: str,
    num_questions: int
) -> list[dict[str, str]]:
    """
    Intelligent heuristic fallback question generator when API is offline.
    """
    c_skills = candidate.get("skills", [])
    if isinstance(c_skills, str):
        c_skills = [s.strip() for s in c_skills.split(",") if s.strip()]

    j_skills = job.get("required_skills", [])
    if isinstance(j_skills, str):
        j_skills = [s.strip() for s in j_skills.split(",") if s.strip()]

    all_skills = list(dict.fromkeys((j_skills or []) + (c_skills or []) + ["Problem Solving", "System Architecture"]))
    j_title = job.get("job_title", "Software Engineer")

    diff_level = difficulty if difficulty in ["Beginner", "Intermediate", "Advanced"] else "Intermediate"

    generated = []

    # 1. Technical Questions
    for skill in all_skills[:3]:
        generated.append({
            "question": f"Explain key concepts and best practices when implementing {skill} in a production {j_title} application.",
            "category": "Technical",
            "difficulty": diff_level,
            "expected_skill": skill,
        })

    # 2. Behavioural Questions
    generated.append({
        "question": "Describe a time when you had conflicting priorities or tight deadlines. How did you handle communication with stakeholders?",
        "category": "Behavioural",
        "difficulty": diff_level,
        "expected_skill": "Communication & Prioritization",
    })
    generated.append({
        "question": "How do you approach receiving constructive feedback on code reviews or technical architecture choices?",
        "category": "Behavioural",
        "difficulty": diff_level,
        "expected_skill": "Team Collaboration",
    })

    # 3. Situational Questions
    generated.append({
        "question": f"If a critical performance bottleneck or bug occurs in the {j_title} system during peak hours, what step-by-step diagnostic workflow would you follow?",
        "category": "Situational",
        "difficulty": diff_level,
        "expected_skill": "Troubleshooting & Problem Solving",
    })
    generated.append({
        "question": f"Imagine you need to introduce a new technology or refactor a legacy module for the {j_title} role. How would you evaluate risks and pitch the change to your team?",
        "category": "Situational",
        "difficulty": diff_level,
        "expected_skill": "Technical Decision Making",
    })

    # 4. Follow-up Questions (Based on Candidate resume skills & projects)
    for skill in (c_skills[:3] if c_skills else ["Software Engineering", "System Architecture"]):
        generated.append({
            "question": f"Based on your background with {skill}, what was the most technical trade-off you had to make in one of your recent projects?",
            "category": "Follow-up",
            "difficulty": diff_level,
            "expected_skill": skill,
        })

    # Pad extra questions if requested num_questions is higher
    extra_cats = ["Technical", "Situational", "Behavioural", "Follow-up"]
    extra_idx = 0
    while len(generated) < num_questions:
        cat = extra_cats[extra_idx % len(extra_cats)]
        sk = all_skills[extra_idx % len(all_skills)]
        generated.append({
            "question": f"How do you ensure high quality, reliability, and security when deploying solutions for {sk} in a {j_title} role?",
            "category": cat,
            "difficulty": diff_level,
            "expected_skill": sk,
        })
        extra_idx += 1

    return generated[:num_questions]


def regenerate_single_question(
    job_data: dict[str, Any],
    category: str = "Technical",
    current_question: str = "",
    skill: str = "",
    api_key: str | None = None
) -> dict[str, Any]:
    """
    Regenerates a single interview question via Groq API.
    """
    j_title = job_data.get("job_title", "Software Engineer")
    j_skills = job_data.get("required_skills", [])
    if isinstance(j_skills, list):
        j_skills_str = ", ".join([str(s) for s in j_skills])
    else:
        j_skills_str = str(j_skills or "General Software Engineering")

    target_skill = skill or (j_skills[0] if isinstance(j_skills, list) and j_skills else "Core Domain")

    prompt = f"""Generate a single NEW, distinct interview question for a candidate interviewing for the role '{j_title}'.
Category: {category}
Target Skill: {target_skill}
Required Role Skills: {j_skills_str}

Previous question to replace (DO NOT REPEAT):
"{current_question}"

Return raw valid JSON only adhering strictly to this schema:
{{
  "question": "Clear, specific technical question",
  "category": "{category}",
  "difficulty": "Intermediate",
  "expected_skill": "{target_skill}"
}}
"""
    try:
        raw_json = call_groq_api(prompt, api_key=api_key)
        parsed = json.loads(raw_json)
        if isinstance(parsed, dict) and "question" in parsed:
            return {
                "question": str(parsed.get("question")).strip(),
                "category": str(parsed.get("category", category)).strip(),
                "difficulty": str(parsed.get("difficulty", "Intermediate")).strip(),
                "expected_skill": str(parsed.get("expected_skill", target_skill)).strip(),
            }
    except Exception as exc:
        print(f"[Warning] Single question regeneration failed ({exc}). Using fallback.")

    return {
        "question": f"Can you walk me through your step-by-step approach when implementing solutions for {target_skill} in a production {j_title} application?",
        "category": category,
        "difficulty": "Intermediate",
        "expected_skill": target_skill,
    }
