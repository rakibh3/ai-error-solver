import os
from app.rag import analyzer

def compare_student_project(student_project_name: str, instructor_project: str, instructor_branch: str):
    student_project_dir = os.path.join("student_projects", instructor_project, student_project_name)
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
                
                analysis = analyzer.analyze_code(student_code, instructor_project, instructor_branch)
                results[file] = analysis

    return {"status": "success", "results": results}
