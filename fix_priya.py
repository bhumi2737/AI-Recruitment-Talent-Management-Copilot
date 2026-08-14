"""
Fix and restore Priya Mehta candidate profile in MongoDB and offline storage.
"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "ResumeParser"))

import database as db
import db_auth
import offline_storage

priya_profile = {
    "candidate_id": "6a53961269254e68d40dff00",
    "full_name": "Priya Mehta",
    "email": "priya.mehta@example.com",
    "phone": "+91 98765 12345",
    "skills": ["Python", "PyTorch", "Docker", "Machine Learning", "TensorFlow", "Deep Learning", "REST APIs", "Git", "SQL"],
    "education": "M.Tech in Artificial Intelligence | IIT Delhi (2020-2022) | CGPA: 9.3/10\nB.Tech in Computer Science | Delhi University (2016-2020)",
    "experience": "Senior AI & Machine Learning Engineer | DataVision AI (2022 - Present)\n• Designed and deployed PyTorch deep learning models for NLP and computer vision.\n• Containerized microservices using Docker and Python REST APIs.",
    "certifications": "AWS Certified Machine Learning - Specialty\nDeepLearning.AI TensorFlow Developer Certificate",
    "projects": "AI Resume & Applicant Screening Engine – PyTorch, Docker, FastAPI.",
    "application_status": "Interview",
    "recruitment_stage": "Interview",
    "raw_text": "Priya Mehta\nSenior AI & Machine Learning Engineer\nEmail: priya.mehta@example.com\nSkills: Python, PyTorch, Docker, Machine Learning, Deep Learning, REST APIs, Git, SQL"
}

# Update MongoDB if available
try:
    with db.get_mongo_client() as client:
        col = client[db.MONGO_CONFIG["dbname"]][db.MONGO_CONFIG["collection"]]
        col.update_one({"email": "priya.mehta@example.com"}, {"$set": priya_profile}, upsert=True)
        print("[DB] Updated Priya Mehta in MongoDB")
except Exception as e:
    print(f"[DB Warning] MongoDB update: {e}")

# Update offline storage
offline_storage.upsert_offline_record("candidates", "6a53961269254e68d40dff00", priya_profile)
print("[Offline] Updated Priya Mehta in offline cache")
