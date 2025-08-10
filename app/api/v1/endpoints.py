from fastapi import APIRouter, HTTPException, UploadFile, File
from app.services import indexing_service, project_service, analysis_service

router = APIRouter()

@router.post("/index-instructor-project/{project_name}/{branch_name}")
def index_project(project_name: str, branch_name: str):
    result = indexing_service.index_instructor_project(project_name, branch_name)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@router.post("/upload/{project_name}")
def upload_project(project_name: str, file: UploadFile = File(...)):
    result = project_service.save_student_project(project_name, file)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.get("/instructor-projects")
def list_instructor_projects():
    return project_service.list_instructor_projects()

@router.get("/instructor-projects/{project_name}/branches")
def list_project_branches(project_name: str):
    return project_service.list_project_branches(project_name)

@router.get("/student-projects/{project_name}")
def list_student_projects(project_name: str):
    return project_service.list_student_projects(project_name)

@router.get("/compare/{student_project_name}")
def compare_project(student_project_name: str, instructor_project: str, instructor_branch: str):
    result = analysis_service.compare_student_project(student_project_name, instructor_project, instructor_branch)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
