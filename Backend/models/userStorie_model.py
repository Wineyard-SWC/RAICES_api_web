from pydantic import BaseModel
from enum import Enum
from typing import List, Optional, Literal, Tuple

class PriorityEnum(str, Enum):
    high = 'High'
    medium = 'Medium'
    low = 'Low'

class AcceptanceCriteriaData(BaseModel):
    id: str 
    description: str # <- Descripcion del criterio de aceptacion
    date_completed: str # <- Dia en que fue completada
    date_created: str   # <- Dia en que fue creada
    date_modified: str  # <- Dia en que fue la ultima modificacion
    # id del usuario que la termino y su nombre
    finished_by: Tuple[str, str]
    # id del usuario que la creo y su nombre 
    # en caso de ser creado por la ia los valores seran RAICES_IA,RAICES_IA 
    created_by:  Tuple[str, str]
    # id del ultimo usuario que la modifico y su nombre 
    modified_by: Tuple[str, str]

class Comment(BaseModel):
    id: str
    user_id: str
    user_name: str
    text: str
    timestamp: str

class Workingusers(BaseModel):
    users: Tuple[str, str]

class UserStory(BaseModel):
    uuid: Optional[str] = None
    idTitle: Optional[str]  = None# Ejemplo: US-001
    title: Optional[str]= None
    comments: Optional[List[Comment]] = None
    status_khanban: Optional[Literal["Backlog","To Do","In Progress","In Review","Done"]]= None
    description: Optional[str] = None
    priority: Optional[PriorityEnum]= None
    points: Optional[int]= None
    acceptanceCriteria: Optional[List[AcceptanceCriteriaData]]= None
    epicRef: Optional[str] = None  # idTitle de la épica (ej. EPIC-001)
    projectRef: Optional[str] = None # ID del proyecto
    total_tasks: Optional[int]= None
    task_completed: Optional[int]= None
    task_list: Optional[List[str]]= None
    assigned_sprint: Optional[str]= None
    completed_acceptanceCriteria: Optional[int]= None
    total_acceptanceCriteria: Optional[int]= None
    date_completed: Optional[str]= None
    deadline: Optional[str]= None
    assignee: Optional[List[Workingusers]]= None

class UserStoryResponse(UserStory):
    id: str  # ID de Firestore (se mantiene por compatibilidad)

class StatusUpdate(BaseModel):
    status_khanban: Literal["Backlog","To Do","In Progress","In Review","Done"]

