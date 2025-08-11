import uvicorn
from fastapi import FastAPI
from app.api.student import router as student_router
from app.api.instructor import router as instructor_router

app = FastAPI()

app.include_router(student_router, prefix="/api/v1/student")
app.include_router(instructor_router, prefix="/api/v1/instructor")

@app.get("/")
def read_root():
    return {"message": "Server is running"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)