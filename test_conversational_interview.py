"""
Automated Test Suite for Conversational AI Interview Engine
-------------------------------------------------------------
Verifies:
1. Candidate greeting generation by name and job role.
2. Deeper technical follow-up question generation on strong/knowledgeable answers.
3. Graceful topic skipping on answers indicating missing skill.
4. Turn history storage containing question, answer, timestamp, and AI reasoning.
5. Post-interview evaluation submission.
"""

import os
import sys
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), "ResumeParser"))

import db_applications
import db_interview_evaluator
import db_interviews
import db_jobs
import conversational_ai_interview


class TestConversationalAIInterview(unittest.TestCase):

    def setUp(self):
        db_applications.clear_applications()

        self.job_id = db_jobs.create_job({
            "job_title": "Python Backend Developer",
            "company_name": "Tech Corp",
            "required_skills": ["Python", "FastAPI", "Docker", "PostgreSQL"],
            "experience_required": "3+ Years",
            "job_description": "Building backends using Python, FastAPI, Docker, and PostgreSQL."
        })

        self.candidate = {
            "candidate_id": "CAND-RAHUL",
            "full_name": "Rahul Sharma",
            "email": "rahul@example.com",
            "skills": ["Python", "FastAPI", "Docker"],
            "experience": "3 years experience",
            "education": "B.Tech CS"
        }

        job = db_jobs.get_job_by_id(self.job_id)
        db_applications.evaluate_and_apply(self.candidate, job)

        # Create interview assignment
        ok_intv, msg_intv, iid = db_interviews.create_interview_assignment(
            candidate_id="CAND-RAHUL",
            job_id=self.job_id,
            questions=["Tell me about your background."],
            due_date="2026-08-15"
        )
        self.assertTrue(ok_intv, f"Failed to assign interview: {msg_intv}")
        self.interview_id = iid

    def test_greeting_generation(self):
        """Verify AI greets candidate by name and target job title."""
        greeting = conversational_ai_interview.generate_greeting("Rahul Sharma", "Python Backend Developer")
        self.assertIn("Hello Rahul Sharma", greeting)
        self.assertIn("Welcome to your interview for Python Backend Developer", greeting)
        self.assertIn("Let's begin", greeting)

    def test_deeper_technical_followup_on_strong_answer(self):
        """Verify AI asks deeper follow-up when candidate indicates experience."""
        history = [
            {"question": "Tell me about Docker.", "answer": "I have used Docker in one project."}
        ]
        result = conversational_ai_interview.generate_next_interview_turn(
            candidate_name="Rahul Sharma",
            job_title="Python Backend Developer",
            required_skills=["Docker", "FastAPI", "Python"],
            conversation_history=history,
            latest_answer="I have used Docker in one project."
        )

        self.assertIn("acknowledgement", result)
        self.assertIn("next_question", result)
        self.assertIn("ai_reasoning", result)
        self.assertTrue(len(result["next_question"]) > 5)
        self.assertTrue("reasoning" in result["ai_reasoning"].lower() or len(result["ai_reasoning"]) > 0)

    def test_graceful_topic_skipping_on_missing_skill(self):
        """Verify AI gracefully pivots when candidate states they never used a technology."""
        history = [
            {"question": "Tell me about Docker.", "answer": "I have never used Docker."}
        ]
        result = conversational_ai_interview.generate_next_interview_turn(
            candidate_name="Rahul Sharma",
            job_title="Python Backend Developer",
            required_skills=["Docker", "REST APIs", "Python"],
            conversation_history=history,
            latest_answer="I have never used Docker."
        )

        self.assertIn("No worries", result["acknowledgement"])
        self.assertIn("ai_reasoning", result)
        self.assertTrue(len(result["ai_reasoning"]) > 0)

    def test_turn_storage_and_reasoning(self):
        """Verify stored conversation turns contain question, answer, timestamp, and ai_reasoning."""
        q1 = "Tell me about Docker."
        a1 = "I have used Docker in one project."
        reasoning1 = "Candidate indicated practical experience with Docker. Asking follow-up on CLI commands."

        ok_turn, msg_turn = db_interviews.append_conversational_turn(
            interview_id=self.interview_id,
            question=q1,
            answer=a1,
            ai_reasoning=reasoning1
        )
        self.assertTrue(ok_turn, f"Failed to append turn: {msg_turn}")

        turns = db_interviews.get_conversational_turns(self.interview_id)
        self.assertEqual(len(turns), 1)
        self.assertEqual(turns[0]["question"], q1)
        self.assertEqual(turns[0]["answer"], a1)
        self.assertEqual(turns[0]["ai_reasoning"], reasoning1)
        self.assertIn("timestamp", turns[0])

    def test_post_interview_evaluation(self):
        """Verify interview evaluation happens after interview finishes with full conversation."""
        # Append 3 turns
        db_interviews.append_conversational_turn(self.interview_id, "Tell me about Docker.", "I used Docker for containerization.", "Good knowledge")
        db_interviews.append_conversational_turn(self.interview_id, "How do you build FastAPI apps?", "Using Depends and Pydantic schemas.", "Strong knowledge")
        db_interviews.append_conversational_turn(self.interview_id, "What is PostgreSQL indexing?", "Used B-tree indexes for fast queries.", "Deep knowledge")

        turns = db_interviews.get_conversational_turns(self.interview_id)
        responses_list = [{"question": t["question"], "answer": t["answer"]} for t in turns]

        # Submit interview
        ok_sub, msg_sub = db_interviews.submit_interview_responses(
            interview_id=self.interview_id,
            candidate_id="CAND-RAHUL",
            job_id=self.job_id,
            responses_list=responses_list
        )
        self.assertTrue(ok_sub, f"Submit failed: {msg_sub}")

        # Post-interview evaluation
        ok_eval, msg_eval = db_interview_evaluator.evaluate_and_save_interview(self.interview_id)
        self.assertTrue(ok_eval, f"Evaluation failed: {msg_eval}")

        # Check updated application status
        app = db_applications.get_application("CAND-RAHUL", self.job_id)
        self.assertEqual(app["interview_status"], "Evaluated")
        self.assertIsNotNone(app.get("interview_score"))


if __name__ == "__main__":
    unittest.main()
