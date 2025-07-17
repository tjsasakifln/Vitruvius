# Production use requires a separate commercial license from the Licensor.
# For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.

from fastapi import FastAPI
from .api.v1.endpoints import projects, auth, analytics, integrations, collaboration

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
app.include_router(analytics.router, prefix="/api", tags=["analytics"])
app.include_router(integrations.router, prefix="/api", tags=["integrations"])
app.include_router(collaboration.router, prefix="/api", tags=["collaboration"])