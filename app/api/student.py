from fastapi import APIRouter, HTTPException, UploadFile, File
from app.services import student_service


router = APIRouter()

@router.post("/upload/{project_name}")
def upload_project(project_name: str, file: UploadFile = File(...)):
    result = student_service.save_student_project(project_name, file)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.get("/student-projects")
def list_all_student_projects():
    return student_service.list_all_student_projects()


