"""
Automated Test Suite for Voice & Conversational AI Interview Engine
---------------------------------------------------------------------
Verifies:
1. Groq Whisper speech-to-text input validation & error formatting.
2. Structured message history schema (message_id, sender, message_text, timestamp, is_voice, ai_reasoning).
3. Groq Llama post-interview evaluation (Technical, Communication, Problem Solving, Confidence, Overall Score).
4. PDF report generation buffer output.
"""

import os
import sys
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), "ResumeParser"))

import db_applications
import db_interview_evaluator
import db_interviews
import db_jobs
import groq_whisper_service
import interview_pdf_report


class TestVoiceConversationalInterview(unittest.TestCase):

    def setUp(self):
        db_applications.clear_applications()

        self.job_id = db_jobs.create_job({
            "job_title": "AI Platform Engineer",
            "company_name": "DeepTech Labs",
            "required_skills": ["Python", "PyTorch", "FastAPI", "Groq API"],
            "experience_required": "4+ Years",
            "job_description": "Building real-time AI agents and voice pipelines."
        })

        self.candidate = {
            "candidate_id": "CAND-VOICE-USER",
            "full_name": "Anita Verma",
            "email": "anita@example.com",
            "skills": ["Python", "PyTorch", "FastAPI"],
            "experience": "4 years AI engineering",
            "education": "M.Tech AI"
        }

        job = db_jobs.get_job_by_id(self.job_id)
        db_applications.evaluate_and_apply(self.candidate, job)

        ok_intv, msg_intv, iid = db_interviews.create_interview_assignment(
            candidate_id="CAND-VOICE-USER",
            job_id=self.job_id,
            questions=["Tell me about your AI background."],
            due_date="2026-08-25"
        )
        self.assertTrue(ok_intv)
        self.interview_id = iid

    def test_groq_whisper_short_audio_validation(self):
        """Verify Groq Whisper service handles short/empty audio gracefully."""
        short_bytes = b"tiny"
        ok, msg = groq_whisper_service.transcribe_audio_groq(short_bytes)
        self.assertFalse(ok)
        self.assertIn("Audio recording is too short", msg)

    def test_structured_chat_message_schema(self):
        """Verify chat messages store message_id, sender, text, timestamp, is_voice, and ai_reasoning."""
        # Append AI Question
        ok1, msg1, doc1 = db_interviews.append_chat_message(
            interview_id=self.interview_id,
            sender="AI",
            message_text="Tell me about your experience with PyTorch and Whisper.",
            is_voice=False,
            ai_reasoning="Opening technical skill question."
        )
        self.assertTrue(ok1)
        self.assertIn("MSG-", doc1["message_id"])

        # Append Candidate Voice Response
        ok2, msg2, doc2 = db_interviews.append_chat_message(
            interview_id=self.interview_id,
            sender="Candidate",
            message_text="I have built voice recognition pipelines using Whisper and PyTorch.",
            is_voice=True,
            ai_reasoning=""
        )
        self.assertTrue(ok2)
        self.assertTrue(doc2["is_voice"])

        messages = db_interviews.get_interview_messages(self.interview_id)
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[1]["sender"], "Candidate")
        self.assertTrue(messages[1]["is_voice"])

    def test_post_interview_llama_evaluation(self):
        """Verify post-interview evaluation computes scores across Technical, Communication, Problem Solving, & Confidence."""
        db_interviews.append_chat_message(self.interview_id, "AI", "Explain how you handle model latency in production.", False, "Latency question")
        db_interviews.append_chat_message(self.interview_id, "Candidate", "We optimized inference by using model quantization and TensorRT caching.", True, "")
        db_interviews.append_chat_message(self.interview_id, "AI", "Excellent. How did you monitor model drift?", False, "Follow up")
        db_interviews.append_chat_message(self.interview_id, "Candidate", "We tracked embedding distribution shifts using Evidently AI and Prometheus alerts.", False, "")

        ok_eval, msg_eval = db_interview_evaluator.evaluate_and_save_interview(self.interview_id)
        self.assertTrue(ok_eval, f"Evaluation failed: {msg_eval}")

        summary = db_interview_evaluator.get_interview_summary(self.interview_id)
        self.assertIsNotNone(summary)
        self.assertIn("overall_interview_score", summary)
        self.assertIn("avg_technical_score", summary)
        self.assertIn("avg_communication_score", summary)
        self.assertIn("avg_problem_solving_score", summary)
        self.assertIn("avg_confidence_score", summary)
        self.assertIn(summary["final_recommendation"], ["Highly Recommended", "Recommended"])

    def test_pdf_interview_report_generation(self):
        """Verify PDF report generator creates valid non-empty PDF bytes."""
        db_interviews.append_chat_message(self.interview_id, "AI", "What are your core strengths?", False, "Intro")
        db_interviews.append_chat_message(self.interview_id, "Candidate", "Strong PyTorch and FastAPI experience.", True, "")

        db_interview_evaluator.evaluate_and_save_interview(self.interview_id)
        eval_list = db_interview_evaluator.get_evaluations_by_interview(self.interview_id)
        summary = db_interview_evaluator.get_interview_summary(self.interview_id)

        job = db_jobs.get_job_by_id(self.job_id)
        pdf_bytes = interview_pdf_report.generate_interview_pdf_report(
            self.candidate, job, self.interview_id, eval_list, summary
        )

        self.assertTrue(len(pdf_bytes) > 500)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
