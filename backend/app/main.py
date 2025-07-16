from fastapi import FastAPI
from .api.v1.endpoints import projects, auth

app = FastAPI(
    title="Vitruvius API",
    description="AI-Powered SaaS Platform for BIM Project Coordination",
    version="1.0.0"
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Vitruvius API"}

# Include API routers
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(projects.router, prefix="/api", tags=["projects"])

