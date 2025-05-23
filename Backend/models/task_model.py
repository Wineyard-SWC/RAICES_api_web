from pydantic import BaseModel
from typing import List, Optional, Literal, Tuple
from pydantic import validator
from datetime import datetime

class StatusUpdate(BaseModel):
    status_khanban: Literal["Backlog","To Do","In Progress","In Review","Done"]

class Comment(BaseModel):
    id: str
    user_id: str
    user_name: str
    text: str
    timestamp: str


class TaskBurndownChart(BaseModel):
    story_points: int=None
    status_khanban: Literal["Backlog","To Do","In Progress","In Review","Done"]=None
    
class GraphicsRequest(BaseModel):
    projectId: str
    tasks: Optional[List[TaskBurndownChart]] = []


class TaskFormData(BaseModel):
    id:Optional[str] = None 
    title: Optional[str] = None
    description: Optional[str]= None
    user_story_id: Optional[str]= None
    assignee: Optional[List[Tuple[str, str]]] = None
    sprint_id: Optional[str] = None
    status_khanban: Literal["Backlog","To Do","In Progress","In Review","Done"] = None 
    priority: Optional[Literal["High","Medium","Low"]] = None
    story_points: Optional[int] = None
    deadline: Optional[str] = None
    comments: Optional[List[Comment]]=None
    created_by: Optional[Tuple[str, str]]  = None    
    modified_by: Optional[Tuple[str, str]] = None
    finished_by: Optional[Tuple[str, str]] = None
    date_created: Optional[str] = None
    date_modified: Optional[str] = None
    date_completed: Optional[str] = None


class TaskResponse(TaskFormData):
    id: str
    user_story_title: Optional[str]
    assignee_id: Optional[List[Tuple[str,str]]] = []
    sprint_name: Optional[str]
    created_at: str
    updated_at: str
    comments: List[Comment]

    @validator('assignee_id', pre=True)
    def normalize_assignee_id(cls, v):
        if v is None:
            return []
        normalized = []
        for item in v:
            if isinstance(item, dict):
                normalized.append((item.get('id', ''), item.get('name', '')))
            elif isinstance(item, (list, tuple)) and len(item) == 2:
                normalized.append((item[0], item[1]))
            else:
                raise ValueError(f"Invalid assignee_id item: {item!r}")
        return normalized
    

    @validator('created_at', 'updated_at', pre=True)
    def convert_timestamp(cls, v):
        if v is None:
            return ""
        if hasattr(v, 'isoformat'):
            return v.isoformat()
        if hasattr(v, 'seconds'):
            # Firestore Timestamp object
            return datetime.fromtimestamp(v.seconds).isoformat()
        return str(v)
    
class TaskPartialKhabanResponse(BaseModel):
    id: str
    user_story_title: Optional[str]
    assignee_id: Optional[List[Tuple[str,str]]] = []
    sprint_name: Optional[str]
    created_at: str
    updated_at: str

    @validator('assignee_id', pre=True)
    def normalize_assignee_id(cls, v):
        if v is None:
            return []
        normalized = []
        for item in v:
            if isinstance(item, dict):
                normalized.append((item.get('id', ''), item.get('name', '')))
            elif isinstance(item, (list, tuple)) and len(item) == 2:
                normalized.append((item[0], item[1]))
            else:
                raise ValueError(f"Invalid assignee_id item: {item!r}")
        return normalized
    
