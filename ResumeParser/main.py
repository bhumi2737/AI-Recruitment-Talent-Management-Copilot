"""
FastAPI Server Entry Point
--------------------------
Starts the backend web server for HireFlow AI.
Exposes Job description REST APIs.
"""

import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import job_routes
import jd_routes
import auth_routes

# Initialize FastAPI App
app = FastAPI(
    title="HireFlow AI API",
    description="Backend API services supporting candidate processing, auth, and Job Description management.",
    version="1.0.0"
)

# CORS Configuration (allows Streamlit frontend to interact with the API in production)
frontend_origin = os.getenv("FRONTEND_URL", "*")
allowed_origins = [origin.strip() for origin in frontend_origin.split(",") if origin.strip()] if frontend_origin != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi import Request
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';"
    return response

# Include Job router
app.include_router(job_routes.router)
# Include JD Match router
app.include_router(jd_routes.router)
# Include Auth router
app.include_router(auth_routes.router)


@app.get("/", tags=["Health"])
def health_check():
    """
    Service health check endpoint.
    """
    return {
        "status": "healthy",
        "service": "HireFlow AI API",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host=host, port=port)
