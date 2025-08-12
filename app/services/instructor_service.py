import os
import shutil
from datetime import datetime
from typing import Dict, Any, List
from app.services import vector_store_service

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

def delete_instructor_project(project_name: str) -> Dict[str, Any]:
   
    instructor_projects_dir = "instructor_projects"
    project_path = os.path.join(instructor_projects_dir, project_name)
    
    # Check if project exists
    if not os.path.isdir(project_path):
        return {
            "status": "error",
            "message": f"Instructor project '{project_name}' not found"
        }
    
    try:
        # Get list of branches before deletion for cleanup and reporting
        branches = []
        if os.path.isdir(project_path):
            branches = [d for d in os.listdir(project_path) 
                       if os.path.isdir(os.path.join(project_path, d))]
        
        # Clean up vector store collections for all branches
        vector_cleanup_results = []
        for branch_name in branches:
            try:
                cleanup_result = vector_store_service.delete_indexed_project(project_name, branch_name)
                vector_cleanup_results.append({
                    "branch": branch_name,
                    "status": cleanup_result.get("status", "unknown"),
                    "message": cleanup_result.get("message", "")
                })
            except Exception as e:
                # Log but don't fail the entire operation for vector cleanup errors
                vector_cleanup_results.append({
                    "branch": branch_name,
                    "status": "error",
                    "message": f"Vector cleanup failed: {str(e)}"
                })
        
        # Delete the project directory
        shutil.rmtree(project_path)
        
        return {
            "status": "success",
            "message": f"Successfully deleted instructor project '{project_name}' with {len(branches)} branches",
            "project_name": project_name,
            "branches_deleted": branches,
            "vector_cleanup_results": vector_cleanup_results,
            "deleted_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to delete instructor project '{project_name}': {str(e)}"
        }



