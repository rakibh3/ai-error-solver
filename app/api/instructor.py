from fastapi import APIRouter, HTTPException, Path, Query
from typing import Union
from app.services import instructor_service
from app.services import indexing_service
from app.services import analysis_service
from app.services import vector_store_service
from app.schemas.schemas import (
    CompareRequest, 
    IndexedProjectsResponse, 
    DeleteProjectResponse,
    ErrorResponse
)

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
def get_all_indexed_projects():
    """
    Get all indexed projects from the vector database.
    
    Returns:
        IndexedProjectsResponse: List of all indexed projects with their metadata
    """
    result = vector_store_service.get_all_indexed_projects()
    
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    
    return result

@router.delete(
    "/indexed-projects/{project_name}/{branch_name}",
    response_model=Union[DeleteProjectResponse, ErrorResponse],
    summary="Delete an indexed project",
    description="Delete a specific indexed project from the vector database by project name and branch",
    responses={
        200: {
            "description": "Successfully deleted indexed project",
            "model": DeleteProjectResponse
        },
        404: {
            "description": "Indexed project not found",
            "model": ErrorResponse
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse
        }
    }
)
def delete_indexed_project(
    project_name: str = Path(..., description="Name of the project to delete"),
    branch_name: str = Path(..., description="Branch name of the project to delete")
):
    """
    Delete a specific indexed project from the vector database.
    
    Args:
        project_name: Name of the project to delete
        branch_name: Branch name of the project to delete
        
    Returns:
        DeleteProjectResponse: Details about the deletion operation
    """
    result = vector_store_service.delete_indexed_project(project_name, branch_name)
    
    if result["status"] == "error":
        # Check if it's a not found error
        if "not found" in result["message"].lower():
            raise HTTPException(status_code=404, detail=result["message"])
        else:
            raise HTTPException(status_code=500, detail=result["message"])
    
    return result

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