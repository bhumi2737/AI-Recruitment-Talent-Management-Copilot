"""
AI Interview Evaluator Module using Groq API & Rigorous Senior Technical Interviewer Rules
-----------------------------------------------------------------------------------------
Evaluates candidate Q&A responses realistically as an experienced Senior Technical Interviewer.
Strict Rules Enforced:
1. No generic feedback or score inflation.
2. Evaluate actual response content (flags "abcd", "test", "ok", single words, and short filler).
3. Detect irrelevancy (e.g. backend frameworks for frontend/React questions).
4. Demand technical depth & accuracy (flags single-mechanism answers like "JWT" missing HTTPS, CORS, Rate Limiting, etc.).
5. Dynamic scoring for Technical, Communication, Confidence, and Overall scores.
6. Generate honest Strengths, Weaknesses, and specific Improvements without hallucinating knowledge.
7. Realistic final recommendation (Highly Recommended, Recommended, Needs Improvement, Not Recommended).
"""

import json
import os
import datetime
from typing import Any
import ai_question_generator as ai_gen


SENIOR_INTERVIEWER_SYSTEM_PROMPT = """You are an experienced Senior Technical Interviewer and Hiring Manager evaluating candidate technical responses.

CRITICAL EVALUATION RULES:
1. NEVER GENERATE GENERIC FEEDBACK:
   - Do NOT use repeated stock phrases like "Clear technical explanation provided", "Good communication", or "Strong understanding".
   - Every evaluation MUST be unique, specific, and based ONLY on the candidate's actual text.

2. EVALUATE THE ACTUAL ANSWER (NO SCORE INFLATION):
   - If the candidate writes short, filler, or incomplete answers (e.g., "abcd", "test", "ok", "yes", "javascript", "node"), YOU MUST:
     • Explicitly state that the response is incomplete or filler.
     • Explain why it fails to answer the technical scenario.
     • Assign low technical, communication, and confidence scores (0 to 25).
     • Provide actionable feedback on how to construct a real answer.

3. DETECT IRRELEVANT / OFF-TOPIC ANSWERS:
   - Example: If the question asks about React tools, and candidate answers "Node.js Express.js", explain that Node.js and Express.js are backend technologies and do NOT answer the React-specific question.
   - Penalize technical accuracy heavily when domain or stack mismatch occurs.

4. DEMAND TECHNICAL ACCURACY & BREADTH:
   - Single-mechanism or superficial answers (e.g., answering "JWT" to "How do you secure production applications?") are INCOMPLETE.
   - Explicitly note missing production concepts (e.g., HTTPS, CORS, Rate Limiting, Input Validation, Secrets Management, Security Headers, OWASP Top 10).
   - Do NOT give high scores (>60) for superficial single-word or single-concept answers.

5. DYNAMIC & REALISTIC SCORING:
   - Technical Score (0-100): Reflects correctness, depth, and domain relevance.
   - Communication Score (0-100): Reflects clarity, structure, and articulation.
   - Confidence Score (0-100): High ONLY if detailed, using correct terminology, providing examples, and showing reasoning. Low if vague, brief, or incorrect.
   - Overall Score (0-100): Weighted synthesis of technical depth and completeness.

6. AI FEEDBACK STRUCTURE:
   - Must contain:
     a) What the candidate answered correctly (if any).
     b) Important missing concepts or gaps.
     c) Relevancy verification (whether it actually answered the question asked).
     d) Specific, concrete steps for technical improvement.

7. STRENGTHS & WEAKNESSES:
   - Generate strengths ONLY if supported by actual text in the answer. NEVER invent or hallucinate strengths.
   - Explicitly list actual weaknesses found.

8. BE HONEST & PROFESSIONAL:
   - If the candidate performs poorly, report it objectively and professionally without score inflation.
"""


def evaluate_single_answer_ai(
    question: str,
    answer: str,
    job_data: dict[str, Any],
    groq_api_key: str | None = None
) -> dict[str, Any]:
    """
    Evaluates a candidate's answer to a single interview question using Senior Technical Interviewer prompt guidelines.
    Returns dict: technical_score, communication_score, confidence_score, overall_score, strengths, improvements, feedback.
    """
    j_title = job_data.get("job_title", "Position")
    j_skills = job_data.get("required_skills", [])
    if isinstance(j_skills, list):
        j_skills_str = ", ".join([str(s) for s in j_skills])
    else:
        j_skills_str = str(j_skills or "General Software Engineering")

    prompt = f"""{SENIOR_INTERVIEWER_SYSTEM_PROMPT}

EVALUATION CONTEXT:
Target Job Position: {j_title}
Required Job Skills: {j_skills_str}

Interview Question Asked:
"{question}"

Candidate's Actual Response:
<user_data>
"{answer[:5000]}"
</user_data>

Required Output JSON Schema (STRICT JSON ONLY):
{{
  "technical_score": integer (0 to 100),
  "communication_score": integer (0 to 100),
  "confidence_score": integer (0 to 100),
  "overall_score": integer (0 to 100),
  "strengths": ["Specific strength 1", "Specific strength 2"],
  "improvements": ["Specific missing concept/improvement 1", "Specific missing concept/improvement 2"],
  "feedback": "Honest, detailed technical evaluation analyzing answer correctness, relevancy, gaps, and missing concepts."
}}

Return raw valid JSON only. Do not add markdown code blocks or text outside JSON.
"""

    try:
        raw_json = ai_gen.call_groq_api(prompt, api_key=groq_api_key)
        parsed = json.loads(raw_json)
        if isinstance(parsed, dict) and "overall_score" in parsed:
            return sanitize_evaluation_result(parsed, question, answer)
    except Exception as exc:
        print(f"[Warning] Groq API evaluation failed ({exc}). Using heuristic evaluation engine.")

    # Fallback Evaluation Engine
    return fallback_evaluate_single_answer(question, answer, job_data)


def sanitize_evaluation_result(parsed: dict[str, Any], question: str, answer: str) -> dict[str, Any]:
    """Ensure evaluation outputs adhere to strict bounds and non-generic formatting."""
    def clamp(val, default=50):
        try:
            return max(0, min(100, int(val)))
        except (ValueError, TypeError):
            return default

    ans_clean = str(answer or "").strip().lower()
    words = ans_clean.split()
    word_count = len(words)

    is_filler = word_count < 4 or ans_clean in ["abcd", "test", "ok", "hi", "yes", "no", "na", "n/a", "none", "type", "hello"]

    if is_filler:
        tech = min(15, clamp(parsed.get("technical_score"), 5))
        comm = min(20, clamp(parsed.get("communication_score"), 10))
        conf = min(15, clamp(parsed.get("confidence_score"), 10))
        overall = min(15, clamp(parsed.get("overall_score"), 8))
        strengths = ["No technical strengths demonstrated due to incomplete response."]
        improvements = ["Provide a complete, detailed technical answer addressing the core question."]
        feedback = f"The candidate provided a filler/incomplete response ('{answer}'). This does not address the question and lacks technical content."
    else:
        tech = clamp(parsed.get("technical_score"), 50)
        comm = clamp(parsed.get("communication_score"), 55)
        conf = clamp(parsed.get("confidence_score"), 50)
        overall = clamp(parsed.get("overall_score"), round((tech * 0.5) + (comm * 0.3) + (conf * 0.2)))

        strengths = parsed.get("strengths", [])
        if not isinstance(strengths, list) or not strengths:
            strengths = ["Addressed basic concepts mentioned in the prompt."]

        improvements = parsed.get("improvements", [])
        if not isinstance(improvements, list) or not improvements:
            improvements = ["Incorporate practical architectural patterns and production trade-offs."]

        feedback = str(parsed.get("feedback", "Response evaluated against required domain skills.")).strip()

    return {
        "technical_score": tech,
        "communication_score": comm,
        "confidence_score": conf,
        "overall_score": overall,
        "strengths": [str(s) for s in strengths[:3]],
        "improvements": [str(i) for i in improvements[:3]],
        "feedback": feedback,
    }


def fallback_evaluate_single_answer(
    question: str,
    answer: str,
    job_data: dict[str, Any]
) -> dict[str, Any]:
    """
    Rigorously rule-based fallback evaluation engine analyzing answer length, relevance, domain match, and completeness.
    """
    q_lower = str(question or "").lower()
    ans_text = str(answer or "").strip()
    ans_lower = ans_text.lower()
    words = ans_text.split()
    word_count = len(words)

    # 1. Filler / Insufficient / Short Answer Check
    if word_count < 4 or ans_lower in ["abcd", "test", "ok", "hi", "yes", "no", "na", "n/a", "none", "type", "hello"]:
        return {
            "technical_score": 5,
            "communication_score": 10,
            "confidence_score": 10,
            "overall_score": 8,
            "strengths": ["No strengths identified due to insufficient answer content."],
            "improvements": ["Provide a detailed technical answer addressing the question thoroughly."],
            "feedback": f"The response '{ans_text}' is incomplete and lacks technical detail. It does not answer the question asked.",
        }

    # 2. Domain / Stack Relevance Check (e.g. React vs Node/Express)
    react_keywords = ["react", "component", "state", "props", "hook", "jsx", "redux", "virtual dom"]
    backend_keywords = ["node", "express", "mongo", "mongodb", "sql", "postgres", "fastapi", "django"]
    
    is_react_question = "react" in q_lower
    is_backend_answer = any(b in ans_lower for b in backend_keywords) and not any(r in ans_lower for r in react_keywords)

    if is_react_question and is_backend_answer:
        return {
            "technical_score": 25,
            "communication_score": 40,
            "confidence_score": 30,
            "overall_score": 28,
            "strengths": ["Identified web development technologies."],
            "improvements": [
                "Focus answer directly on React frontend tools (Hooks, Redux, Context API) rather than backend tools (Node.js, Express)."
            ],
            "feedback": (
                f"The question specifically asked for React frontend tools, but the response ('{ans_text}') listed backend technologies "
                "(Node.js, Express.js). This indicates a domain mismatch and does not answer the React question directly."
            ),
        }

    # 3. Single Keyword / Partial Answer Check (e.g. "JWT" for security)
    is_security_question = any(term in q_lower for term in ["security", "secure", "production", "protect", "authentication"])
    is_single_concept = word_count <= 5 and ("jwt" in ans_lower or "token" in ans_lower or "ssl" in ans_lower)

    if is_security_question and is_single_concept:
        return {
            "technical_score": 35,
            "communication_score": 45,
            "confidence_score": 35,
            "overall_score": 38,
            "strengths": ["Identified JWT as an authentication mechanism."],
            "improvements": [
                "Elaborate on multi-layer production security: HTTPS, CORS, Rate Limiting, Input Validation, Security Headers, and Secrets Management."
            ],
            "feedback": (
                f"The response '{ans_text}' mentions JWT, which is only one authentication mechanism. "
                "A complete production security answer must address HTTPS, CORS, rate limiting, input validation, and secure header configuration."
            ),
        }

    # 4. Standard Heuristic Analysis
    j_skills = job_data.get("required_skills", [])
    if isinstance(j_skills, str):
        j_skills = [s.strip().lower() for s in j_skills.split(",") if s.strip()]

    matched_skills = [s for s in j_skills if str(s).lower() in ans_lower]

    tech_score = min(90, max(30, 40 + (len(matched_skills) * 15) + min(20, word_count // 12)))
    comm_score = min(90, max(40, 50 + min(25, word_count // 10)))
    conf_score = min(90, max(35, 45 + min(25, word_count // 10) + (10 if len(matched_skills) > 0 else 0)))

    overall_score = round((tech_score * 0.50) + (comm_score * 0.30) + (conf_score * 0.20))

    strengths = []
    if matched_skills:
        strengths.append(f"Demonstrated familiarity with target skills: {', '.join(matched_skills[:2])}.")
    if word_count >= 30:
        strengths.append("Provided a structured written response.")
    if not strengths:
        strengths.append("Attempted to address the interview prompt.")

    improvements = []
    if word_count < 25:
        improvements.append("Expand on specific architectural details and implementation choices.")
    if len(matched_skills) < len(j_skills[:2]):
        improvements.append("Include specific domain terminology and practical frameworks.")

    feedback = (
        f"The candidate response contains {word_count} words and mentions {', '.join(matched_skills) if matched_skills else 'general technical terms'}. "
        f"{'Providing more depth and practical metrics will improve the overall score.' if word_count < 30 else 'Good explanation of concepts.'}"
    )

    return {
        "technical_score": tech_score,
        "communication_score": comm_score,
        "confidence_score": conf_score,
        "overall_score": overall_score,
        "strengths": strengths[:2],
        "improvements": improvements[:2] if improvements else ["Detail concrete project metrics and trade-offs."],
        "feedback": feedback,
    }


def compute_interview_summary(evaluations: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Computes overall summary report metrics and hiring recommendation based on rigorous evaluation rules:
    - 88 - 100 -> Highly Recommended
    - 72 - 87  -> Recommended
    - 55 - 71  -> Needs Improvement
    - Below 55 -> Not Recommended
    """
    if not evaluations:
        return {
            "overall_interview_score": 0,
            "avg_technical_score": 0,
            "avg_communication_score": 0,
            "avg_confidence_score": 0,
            "top_strengths": [],
            "areas_for_improvement": [],
            "final_recommendation": "Not Recommended",
            "summary_notes": "No interview evaluation data recorded."
        }

    valid_evals = [e for e in evaluations if e.get("overall_score", 0) > 0]
    evals_to_use = valid_evals if valid_evals else evaluations

    avg_tech = round(sum([e.get("technical_score", 0) for e in evals_to_use]) / len(evals_to_use))
    avg_comm = round(sum([e.get("communication_score", 0) for e in evals_to_use]) / len(evals_to_use))
    avg_conf = round(sum([e.get("confidence_score", 0) for e in evals_to_use]) / len(evals_to_use))
    overall_score = round(sum([e.get("overall_score", 0) for e in evals_to_use]) / len(evals_to_use))

    # Rigorous Final Recommendation
    if overall_score >= 88 and avg_tech >= 85:
        rec = "Highly Recommended"
    elif overall_score >= 72 and avg_tech >= 68:
        rec = "Recommended"
    elif overall_score >= 55:
        rec = "Needs Improvement"
    else:
        rec = "Not Recommended"

    # Consolidate Strengths and Improvements
    all_strengths = []
    all_improvements = []
    for e in evals_to_use:
        all_strengths.extend(e.get("strengths", []))
        all_improvements.extend(e.get("improvements", []))

    def unique_list(seq):
        seen = set()
        return [x for x in seq if not (x in seen or seen.add(x))]

    summary_notes = (
        f"Candidate achieved an overall score of {overall_score}% across {len(evals_to_use)} interview questions. "
        f"Technical Depth: {avg_tech}%, Communication: {avg_comm}%, Confidence: {avg_conf}%. "
        f"Final Recommendation: {rec}."
    )

    return {
        "overall_interview_score": overall_score,
        "avg_technical_score": avg_tech,
        "avg_communication_score": avg_comm,
        "avg_confidence_score": avg_conf,
        "top_strengths": unique_list(all_strengths)[:4],
        "areas_for_improvement": unique_list(all_improvements)[:4],
        "final_recommendation": rec,
        "summary_notes": summary_notes
    }
