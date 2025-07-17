# Production use requires a separate commercial license from the Licensor.
# For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.v1.endpoints import projects, auth, analytics, integrations, collaboration
from .middleware.rate_limiter import create_rate_limit_middleware
from .core.exceptions import create_error_handler

app = FastAPI(
    title="Vitruvius API",
    description="AI-Powered SaaS Platform for BIM Project Coordination",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware
app.add_middleware(create_rate_limit_middleware)

# Add error handlers
error_handlers = create_error_handler()
for exception_type, handler in error_handlers.items():
    app.add_exception_handler(exception_type, handler)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Vitruvius API"}

# Include API routers
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(projects.router, prefix="/api", tags=["projects"])
app.include_router(analytics.router, prefix="/api", tags=["analytics"])
app.include_router(integrations.router, prefix="/api", tags=["integrations"])
app.include_router(collaboration.router, prefix="/api", tags=["collaboration"])