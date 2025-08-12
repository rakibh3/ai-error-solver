from pydantic import BaseModel
from typing import Optional, List, Union
from datetime import datetime

class CompareRequest(BaseModel):
    student_project_name: str
    student_project_id: str
    instructor_project: str
    instructor_branch: str
    error_message: Optional[str] = None

class IndexedProjectInfo(BaseModel):
    """Model for individual indexed project information"""
    collection_name: str
    project_name: str
    branch_name: str
    vectors_count: int
    indexed_at: str
    vector_size: Optional[int] = None
    distance_metric: Optional[str] = None
    status: Optional[str] = None

class IndexedProjectsResponse(BaseModel):
    """Response model for getting all indexed projects"""
    status: str
    total_indexed_projects: int
    indexed_projects: List[IndexedProjectInfo]
    message: Optional[str] = None

class DeleteProjectResponse(BaseModel):
    """Response model for deleting an indexed project"""
    status: str
    message: str
    collection_name: Optional[str] = None
    project_name: Optional[str] = None
    branch_name: Optional[str] = None
    vectors_deleted: Optional[Union[int, str]] = None
    deleted_at: Optional[str] = None

class ErrorResponse(BaseModel):
    """Standard error response model"""
    status: str = "error"
    message: str
