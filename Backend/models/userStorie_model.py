from pydantic import BaseModel
from enum import Enum
from typing import List

class PriorityEnum(str, Enum):
    high = 'High'
    medium = 'Medium'
    low = 'Low'

class UserStories(BaseModel):
    idTitle: str
    title: str
    description: str
    priority: PriorityEnum
    points: int
    acceptanceCriteria: List[str]
    epicRef: str = None  # ID de la épica a la que pertenece, puede ser opcional

class UserStoriesResponse(UserStories):
    id: str
