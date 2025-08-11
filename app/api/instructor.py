from fastapi import APIRouter, HTTPException
from app.services import instructor_service
from app.services import indexing_service
from app.services import project_service

router = APIRouter()

@router.post("/index-instructor-project/{project_name}")
def index_project(project_name: str):
    result = indexing_service.index_project_branches(project_name)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@router.get("/instructor-projects")
def list_instructor_projects():
    return project_service.list_instructor_projects()

@router.get("/instructor-projects/{project_name}/branches")
def list_project_branches(project_name: str):
    return project_service.list_project_branches(project_name)
