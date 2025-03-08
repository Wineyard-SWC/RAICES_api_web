from .req_models import Requirements
from pydantic import BaseModel
from typing import List

# Ëpicas
class Epic(BaseModel):
    Desc: str
    IDEpic: str
    Name: str
    RelatedReqs: List[Requirements] = []

class EpicResponse(Epic):
    id: str  