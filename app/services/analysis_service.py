import os
from app.rag import analyzer
from typing import Optional

def compare_student_project(student_project_name: str, student_project_id: str, instructor_project: str, instructor_branch: str, error_message: Optional[str] = None):
    student_project_dir = os.path.join("student_projects", student_project_name, student_project_id)
    if not os.path.isdir(student_project_dir):
        return {"error": "Student project not found"}

    # If there's no error message, we can't proceed with error-driven analysis.
    if not error_message:
        return {"error": "An error message is required for analysis."}

    all_student_code = []
    for root, _, files in os.walk(student_project_dir):
        for file in files:
            if file.endswith(('.py', '.js', '.ts', '.tsx', '.html', '.css', '.md', '.json')):
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, student_project_dir)
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    code = f.read()
                    all_student_code.append(f"--- File: {relative_path} ---\n{code}")

    student_code_context = "\n\n".join(all_student_code)

    # Perform a single, error-driven analysis
    analysis = analyzer.analyze_code(
        student_code_context=student_code_context,
        instructor_project_name=instructor_project,
        instructor_branch_name=instructor_branch,
        error_message=error_message
    )

    return {"status": "success", "results": analysis}