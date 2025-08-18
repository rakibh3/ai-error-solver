from fastapi import APIRouter, HTTPException, UploadFile, File, Path, Depends, Form
from app.middleware.role_checker import require_admin
from app.services import student_service
from app.middleware.role_checker import require_role, require_instructor_or_admin, require_admin
from app.models.user import User, UserRole

router = APIRouter()

@router.post("/upload")
def upload_project(project_name: str = Form(...), file: UploadFile = File(...), current_user: User = Depends(require_role(UserRole.STUDENT))):
    result = student_service.save_student_project(project_name, file)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.get("/student-projects")
def list_all_student_projects(current_user: User = Depends(require_instructor_or_admin)):
    return student_service.list_all_student_projects()

@router.delete("/project/{student_project_id}", 
               summary="Delete a student project",
               description="Delete a student project by its ID",
               responses={
                   200: {"description": "Student project successfully deleted"},
                   404: {"description": "Student project not found"},
                   500: {"description": "Internal server error"}
               })
def delete_student_project(
    student_project_id: str = Path(..., description="The UUID of the student project to delete"),
    current_user: User = Depends(require_admin)
):
    result = student_service.delete_student_project(student_project_id)
    
    if result["status"] == "error":
        if "not found" in result["message"].lower():
            raise HTTPException(status_code=404, detail=result["message"])
        else:
            raise HTTPException(status_code=500, detail=result["message"])
    
    return result


