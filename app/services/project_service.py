import os
import shutil
import zipfile
import uuid
from fastapi import UploadFile
from app.utils.cleanup import cleanup_student_project
from app.rag import analyzer
from typing import Optional

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

def compare_student_project(student_project_name: str, student_project_id: str, instructor_project: str, instructor_branch: str, error_message: Optional[str] = None):
    student_project_dir = os.path.join("student_projects", student_project_name, student_project_id)
    if not os.path.isdir(student_project_dir):
        return {"error": "Student project not found"}

    results = {}
    for root, _, files in os.walk(student_project_dir):
        for file in files:
            # Simple check to avoid non-code files
            if file.endswith(('.py', '.js', '.ts', '.tsx', '.html', '.css', '.md', '.json')):
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    student_code = f.read()
                
                analysis = analyzer.analyze_code(student_code, instructor_project, instructor_branch, error_message)
                results[file] = analysis

    return {"status": "success", "results": results}


def list_instructor_projects():
    instructor_projects_dir = "instructor_projects"
    if not os.path.isdir(instructor_projects_dir):
        return []
    return [d for d in os.listdir(instructor_projects_dir) if os.path.isdir(os.path.join(instructor_projects_dir, d))]

def list_project_branches(project_name: str):
    project_dir = os.path.join("instructor_projects", project_name)
    if not os.path.isdir(project_dir):
        return {"error": "Project not found"}
    return [d for d in os.listdir(project_dir) if os.path.isdir(os.path.join(project_dir, d))]



