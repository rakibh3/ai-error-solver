import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from fastapi import HTTPException
from app.services import vector_store_service
from app.services import indexing_service

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



def index_instructor_project(repo_url):
    # Convert HttpUrl object to string if necessary
    repo_url_str = str(repo_url)
    
    # Extract project name from repo URL
    project_name = repo_url_str.rstrip('/').split('/')[-1].replace('.git', '')
    parent_path = Path("instructor_projects") / project_name
    parent_path.mkdir(parents=True, exist_ok=True)

    try:
        # 1️⃣ Get all branches
        cmd = ["git", "ls-remote", "--heads", repo_url_str]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        branches = [
            line.split()[1].replace("refs/heads/", "")
            for line in result.stdout.strip().split("\n")
            if line
        ]
        if not branches:
            raise HTTPException(status_code=404, detail="No branches found in repository")

        cloned_branches = []
        indexing_results = []
        
        for branch in branches:
            branch_dir = parent_path / branch
            branch_dir.mkdir(exist_ok=True)

            try:
                # Clone only that branch
                subprocess.run(
                    [
                        "git", "clone", "--branch", branch, "--single-branch",
                        "--depth", "1", repo_url_str, str(branch_dir)
                    ],
                    check=True
                )

                # Remove .git directory
                git_dir = branch_dir / ".git"
                if git_dir.exists():
                    shutil.rmtree(git_dir)

                cloned_branches.append(branch)
                
                # Index the cloned branch
                print(f"Starting indexing for {project_name}/{branch}")
                index_result = indexing_service.index_instructor_project(project_name, branch)
                indexing_results.append({
                    "branch": branch,
                    "indexing_result": index_result
                })
                
                if index_result.get("status") == "success":
                    print(f"Successfully indexed {project_name}/{branch}")
                else:
                    print(f"Indexing failed for {project_name}/{branch}: {index_result.get('error', 'Unknown error')}")
                    
            except subprocess.CalledProcessError as e:
                # If cloning fails for this branch, continue with others
                print(f"Failed to clone branch {branch}: {e}")
                indexing_results.append({
                    "branch": branch,
                    "indexing_result": {"error": f"Clone failed: {str(e)}"}
                })
                continue

        # Calculate indexing summary
        successful_indexes = sum(1 for result in indexing_results 
                               if result["indexing_result"].get("status") == "success")
        
        return {
            "status": "success",
            "project_name": project_name,
            "parent_folder": str(parent_path),
            "cloned_branches": cloned_branches,
            "indexing_results": indexing_results,
            "indexing_summary": {
                "total_branches": len(branches),
                "successfully_cloned": len(cloned_branches),
                "successfully_indexed": successful_indexes,
                "failed_indexes": len(indexing_results) - successful_indexes
            }
        }

    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Git command failed: {e.stderr}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))