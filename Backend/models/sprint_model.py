from pydantic import BaseModel
from typing import List, Literal, Optional,Tuple
from datetime import datetime

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

class SprintMemberData(BaseModel):
    id: str
    name: str
    role: str
    avatar: Optional[str]
    capacity: int
    allocated: int

class SprintUserStoryData(BaseModel):
    id: str
    title: str
    description: str
    acceptance_criteria: List[AcceptanceCriteriaData]
    tasks: List[str]  
    selected: bool

class SprintFormData(BaseModel):
    name: str
    start_date: datetime
    end_date: datetime
    duration_weeks: int
    status: Literal["planning", "active", "completed"]
    team_members: List[SprintMemberData]
    user_stories: List[SprintUserStoryData]

class SprintResponse(SprintFormData):
    id: str
    project_id: str
    created_at: datetime
    updated_at: datetime
