from fastapi import APIRouter, HTTPException, Path
from typing import Union
from app.services import instructor_service
from app.schemas.schemas import InstructorProjectDeleteResponse, ErrorResponse

router = APIRouter()


@router.get("/instructor-projects")
def list_instructor_projects():
    return instructor_service.list_instructor_projects()

@router.get("/instructor-projects/{project_name}/branches")
def list_project_branches(project_name: str):
    return instructor_service.list_project_branches(project_name)

@router.delete(
    "/instructor-project/{instructor_project_name}",
    response_model=Union[InstructorProjectDeleteResponse, ErrorResponse],
    summary="Delete an instructor project with all branches and associated vector collections",
    description="Delete an entire instructor project including all branches and associated vector collections",
    responses={
        200: {
            "description": "Successfully deleted instructor project",
            "model": InstructorProjectDeleteResponse
        },
        404: {
            "description": "Instructor project not found",
            "model": ErrorResponse
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse
        }
    }
)
def delete_instructor_project(
    instructor_project_name: str = Path(..., description="Name of the instructor project to delete")
):
    """
    Delete an instructor project and all its branches.
    
    This operation will:
    - Delete the entire project directory and all branch subdirectories
    - Clean up all associated vector store collections
    - Return a detailed summary of the deletion operation
    
    The operation is designed to be safe and will return appropriate errors
    if the project doesn't exist or if there are any issues during deletion.
    """
    result = instructor_service.delete_instructor_project(instructor_project_name)
    
    if result["status"] == "error":
        # Check if it's a not found error
        if "not found" in result["message"].lower():
            raise HTTPException(status_code=404, detail=result["message"])
        else:
            raise HTTPException(status_code=500, detail=result["message"])
    
    return result