from fastapi import APIRouter, HTTPException
from app.services import instructor_service
from app.services import indexing_service
from app.services import instructor_service
from app.services import analysis_service
from app.schemas.schemas import CompareRequest

router = APIRouter()

@router.post("/index-instructor-project/{project_name}")
def index_project(project_name: str):
    result = indexing_service.index_project_branches(project_name)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@router.get("/instructor-projects")
def list_instructor_projects():
    return instructor_service.list_instructor_projects()

@router.get("/instructor-projects/{project_name}/branches")
def list_project_branches(project_name: str):
    return instructor_service.list_project_branches(project_name)


@router.post("/compare")
def compare_project(request: CompareRequest):
    result = analysis_service.compare_student_project(
        request.student_project_name,
        request.student_project_id,
        request.instructor_project,
        request.instructor_branch,
        request.error_message
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result