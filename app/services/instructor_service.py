import os

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



