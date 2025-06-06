from pydantic import BaseModel
from typing import Optional, List, Literal, Tuple,Union
from datetime import datetime

class Workingusers(BaseModel):
    users: Tuple[str, str]  # id, name

class StatusUpdate(BaseModel):
    status_khanban: Literal["Backlog","To Do","In Progress","In Review","Done"]

class Comments(BaseModel):
    id: str
    user_id: str
    user_name: str
    text: str
    timestamp: str

class AssigneeData(BaseModel):
    id: str
    name: str

class BugBase(BaseModel):
    title:  Optional[str]=None
    description:  Optional[str]=None
    type: Optional[str]=None
    severity:  Optional[Literal['Blocker', 'Critical', 'Major', 'Minor', 'Trivial']]=None
    priority:  Optional[Literal['Critical', 'High', 'Medium', 'Low', 'Trivial']]=None
    status_khanban: Optional[Literal["Backlog","To Do","In Progress","In Review","Done"]]=None
    bug_status: Optional[Literal['New', 'Triaged', 'In_progress', 'Testing', 'Reopened', 'Resolved', 'Closed']]=None
    projectId:  Optional[str]=None
    taskRelated: Optional[str]=None
    userStoryRelated: Optional[str]=None
    sprintId: Optional[str]=None
    reportedBy:  Optional[Workingusers]=None
    assignee:  Optional[List[Union[AssigneeData,Workingusers]]]=None
    createdAt:  Optional[str]=None
    modifiedAt:  Optional[str]=None
    triageDate: Optional[str]=None
    startedAt: Optional[str]=None
    finishedAt: Optional[str]=None
    closedAt: Optional[str]=None
    environment: Optional[dict]=None
    stepsToReproduce: Optional[List[str]]=None
    expectedBehavior: Optional[str]=None
    actualBehavior: Optional[str]=None
    comments: Optional[List[Comments]]=None
    resolution: Optional[dict]=None
    timeToPrioritize: Optional[float]=None
    timeToAssign: Optional[float]=None
    timeToFix: Optional[float]=None
    reopenCount: Optional[int]=None
    tags: Optional[List[str]]=None
    isRegression: Optional[bool]=None
    relatedBugs: Optional[List[str]]=None
    duplicateOf: Optional[str]=None
    affectedComponents: Optional[List[str]]=None
    affectedUsers: Optional[int]=None
    visibleToCustomers:  Optional[bool]=None

class Bug(BugBase):
    id: str
 