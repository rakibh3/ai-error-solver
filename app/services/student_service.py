import os
import shutil
import zipfile
import uuid
from fastapi import UploadFile
from app.utils.cleanup import cleanup_student_project

def save_student_project(project_name: str, file: UploadFile):
    # Generate a unique ID for the student project
    student_project_id = str(uuid.uuid4())
    student_project_dir = os.path.join("student_projects", project_name, student_project_id)
    os.makedirs(student_project_dir, exist_ok=True)

    # Save the uploaded zip file
    zip_path = os.path.join(student_project_dir, file.filename)
    
    try:
        # Read the content of the uploaded file
        content = file.file.read()
        
        # Write the content to a new file
        with open(zip_path, "wb") as buffer:
            buffer.write(content)

        # Unzip the file
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(student_project_dir)

        # Clean up the zip file
        os.remove(zip_path)

        # Clean up unnecessary directories
        cleanup_student_project(student_project_dir)

        return {"status": "success", "student_project_id": student_project_id}
    except zipfile.BadZipFile:
        return {"error": "The uploaded file is not a valid zip file."}
    except Exception as e:
        # Clean up the created directory in case of an error
        shutil.rmtree(student_project_dir)
        return {"error": f"An unexpected error occurred: {str(e)}"}


def list_all_student_projects():
    all_student_data = []
    base_student_projects_dir = "student_projects"
    if not os.path.isdir(base_student_projects_dir):
        return []

    for project_name in os.listdir(base_student_projects_dir):
        project_path = os.path.join(base_student_projects_dir, project_name)
        if os.path.isdir(project_path):
            for student_id in os.listdir(project_path):
                student_id_path = os.path.join(project_path, student_id)
                if os.path.isdir(student_id_path):
                    all_student_data.append({"project_name": project_name, "student_project_id": student_id})
    return all_student_data

def delete_student_project(student_project_id: str):

    base_student_projects_dir = "student_projects"
    
    # Search for the project containing the student_project_id
    if not os.path.isdir(base_student_projects_dir):
        return {"status": "error", "message": "Student projects directory does not exist"}
    
    for project_name in os.listdir(base_student_projects_dir):
        project_path = os.path.join(base_student_projects_dir, project_name)
        if os.path.isdir(project_path):
            student_path = os.path.join(project_path, student_project_id)
            if os.path.isdir(student_path):
                try:
                    # Delete the student project directory
                    shutil.rmtree(student_path)
                    
                    # Check if the project directory is now empty and remove it if it is
                    if not os.listdir(project_path):
                        os.rmdir(project_path)
                        
                    return {"status": "success", "message": f"Student project {student_project_id} deleted successfully"}
                except Exception as e:
                    return {"status": "error", "message": f"Failed to delete student project: {str(e)}"}
    
    return {"status": "error", "message": f"Student project with ID {student_project_id} not found"}
