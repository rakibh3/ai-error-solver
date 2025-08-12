from fastapi import APIRouter, HTTPException, UploadFile, File, Path
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

@router.delete("/project/{student_project_id}", 
               summary="Delete a student project",
               description="Delete a student project by its ID",
               responses={
                   200: {"description": "Student project successfully deleted"},
                   404: {"description": "Student project not found"},
                   500: {"description": "Internal server error"}
               })
def delete_student_project(
    student_project_id: str = Path(..., description="The UUID of the student project to delete")
):
    result = student_service.delete_student_project(student_project_id)
    
    if result["status"] == "error":
        if "not found" in result["message"].lower():
            raise HTTPException(status_code=404, detail=result["message"])
        else:
            raise HTTPException(status_code=500, detail=result["message"])
    
    return result


