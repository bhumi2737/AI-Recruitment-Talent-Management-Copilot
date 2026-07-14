"""
FastAPI Server Entry Point
--------------------------
Starts the backend web server for the Recruitment Copilot.
Exposes Job description REST APIs.
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import job_routes

# Initialize FastAPI App
app = FastAPI(
    title="AI Recruitment & Talent Management Copilot API",
    description="Backend API services supporting candidate processing and Job Description management.",
    version="1.0.0"
)

# CORS Configuration (allows Streamlit frontend to interact with the API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the exact Streamlit domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Job router
app.include_router(job_routes.router)


@app.get("/", tags=["Health"])
def health_check():
    """
    Service health check endpoint.
    """
    return {
        "status": "healthy",
        "service": "AI Recruitment Copilot API",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
