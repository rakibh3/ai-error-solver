import uvicorn
from fastapi import FastAPI
from app.api.student import router as student_router
from app.api.index import router as index_router
from app.api.project import router as project_router

app = FastAPI(
    title="Error Navigator API",
    description="An AI-powered error solver that helps learners identify and fix errors in their code by comparing it against instructor's master code. The system provides step-by-step solutions with file locations, line numbers, and exact code changes needed. Features include instructor project management with multiple branches, learner project upload via zip files, and RAG-based code comparison using Google Gemini API.",
    version="1.0.0",
    openapi_url="/api/v1/openapi.json",
    contact={
        "name": "Error Navigator",
        "url": "https://error-navigator.com",
    }
)

app.openapi_tags = [
    {
        "name": "Project API",
        "description": "Manage instructor projects and branches. Allows instructors to upload, organize, and maintain multiple project versions for code comparison.",
    },
    {
        "name": "Index API",
        "description": "Vector indexing and search operations. Handles the creation and management of code embeddings for efficient RAG-based comparison.",
    },
    {
        "name": "Student Project API",
        "description": "Student project submission and analysis. Enables learners to upload their code projects and receive AI-powered error detection and step-by-step solutions.",
    },
]

app.include_router(project_router, prefix="/api/v1/project", tags=["Project API"])
app.include_router(index_router, prefix="/api/v1/index", tags=["Index API"])
app.include_router(student_router, prefix="/api/v1/student", tags=["Student Project API"])

@app.get("/", tags=["Root API"])
def read_root():
    return {"message": "Server is running"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)