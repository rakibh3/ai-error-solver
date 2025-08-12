import uvicorn
from fastapi import FastAPI
from app.api.student import router as student_router
from app.api.index import router as index_router
from app.api.project import router as project_router

app = FastAPI()

app.include_router(project_router, prefix="/api/v1/project")
app.include_router(index_router, prefix="/api/v1/index")
app.include_router(student_router, prefix="/api/v1/student")

@app.get("/")
def read_root():
    return {"message": "Server is running"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)