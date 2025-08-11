import os
import shutil

def cleanup_student_project(project_dir: str):
    # Directories to remove
    dirs_to_remove = ["node_modules", "venv", ".venv", ".vercel", ".git", ".next", "__pycache__"]
    for root, dirs, _ in os.walk(project_dir):
        for d in dirs:
            if d in dirs_to_remove:
                shutil.rmtree(os.path.join(root, d), ignore_errors=True)
