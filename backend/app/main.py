from fastapi import FastAPI

app = FastAPI(title="Vitruvius Backend")

@app.get("/")
def read_root():
    return {"message": "Welcome to the Vitruvius API"}

# Include routers from app/api here
# from .api import users, projects
# app.include_router(users.router)
# app.include_router(projects.router)
