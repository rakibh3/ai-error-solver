from fastapi import APIRouter
from app.services import instructor_service

router = APIRouter()


@router.get("/instructor-projects")
def list_instructor_projects():
    return instructor_service.list_instructor_projects()

@router.get("/instructor-projects/{project_name}/branches")
def list_project_branches(project_name: str):
    return instructor_service.list_project_branches(project_name)