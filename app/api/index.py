from fastapi import APIRouter, HTTPException, Path, Query, Depends
from typing import Union
from app.services import indexing_service
from app.services import analysis_service
from app.services import vector_store_service
from app.schemas.schemas import (
    CompareRequest, 
    IndexedProjectsResponse, 
    DeleteProjectResponse,
    ErrorResponse
)
from app.api.project import require_instructor_or_admin
from app.models.user import User


router = APIRouter()

@router.post("/index-instructor-project/{project_name}")
def index_project(project_name: str, current_user: User = Depends(require_instructor_or_admin)):
    result = indexing_service.index_project_branches(project_name)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@router.get(
    "/indexed-projects",
    response_model=Union[IndexedProjectsResponse, ErrorResponse],
    summary="Get all indexed projects",
    description="Retrieve a list of all projects that have been indexed in the vector database",
    responses={
        200: {
            "description": "Successfully retrieved indexed projects",
            "model": IndexedProjectsResponse
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse
        }
    }
)
def get_all_indexed_projects(current_user: User = Depends(require_instructor_or_admin)):
    result = vector_store_service.get_all_indexed_projects()
    
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    
    return result


@router.post("/compare")
def compare_project(request: CompareRequest, current_user: User = Depends(require_instructor_or_admin)):
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