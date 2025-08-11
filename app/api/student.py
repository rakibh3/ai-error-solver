from fastapi import APIRouter, HTTPException, UploadFile, File
from app.services import project_service
from app.schemas.schemas import CompareRequest

router = APIRouter()

@router.post("/upload/{project_name}")
def upload_project(project_name: str, file: UploadFile = File(...)):
    result = project_service.save_student_project(project_name, file)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.get("/student-projects")
def list_all_student_projects():
    return project_service.list_all_student_projects()

@router.post("/compare")
def compare_project(request: CompareRequest):
    result = project_service.compare_student_project(
        request.student_project_name,
        request.student_project_id,
        request.instructor_project,
        request.instructor_branch,
        request.error_message
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
