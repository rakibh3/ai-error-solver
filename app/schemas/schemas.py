from pydantic import BaseModel
from typing import Optional

class CompareRequest(BaseModel):
    student_project_name: str
    student_project_id: str
    instructor_project: str
    instructor_branch: str
    error_message: Optional[str] = None
