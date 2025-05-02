from pydantic import BaseModel
from typing import List, Optional, Literal

class StatusUpdate(BaseModel):
    status_khanban: Literal["Backlog","To Do","In Progress","In Review","Done"]

class Comment(BaseModel):
    id: str
    user_id: str
    user_name: str
    text: str
    timestamp: str

class TaskFormData(BaseModel):
    id:str
    title: str
    description: str
    user_story_id: str
    assignee: str
    sprint_id: Optional[str] = None
    status_khanban: Literal["Backlog","To Do","In Progress","In Review","Done"]
    priority: Literal["High","Medium","Low"]
    story_points: int
    deadline: Optional[str] = None
    comments: List[Comment]

class TaskResponse(TaskFormData):
    id: str
    user_story_title: Optional[str]
    assignee_id: Optional[str]
    sprint_name: Optional[str]
    created_at: str
    updated_at: str
    comments: List[Comment]
