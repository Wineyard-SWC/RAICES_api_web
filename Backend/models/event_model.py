from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel

class EventType(str, Enum):
    meeting = "meeting"
    task = "task"
    deadline = "deadline"

class EventPriority(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"

class RecurrenceFrequency(str, Enum):
    daily = "daily"
    weekly = "weekly"
    biweekly = "biweekly"
    monthly = "monthly"

class Recurrence(BaseModel):
    frequency: RecurrenceFrequency
    end_date: Optional[datetime] = None
    excluded_dates: List[datetime] = []

class EventCreate(BaseModel):
    project_id: str
    sprint_id: str
    created_by: str
    title: str
    description: str
    type: EventType
    priority: EventPriority
    start_date: datetime
    end_date: datetime
    is_all_day: bool = False
    location: Optional[str] = None
    participants: List[str] = []
    related_tasks: List[str] = []
    is_recurring: bool = False
    recurrence: Optional[Recurrence] = None

class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    type: Optional[EventType] = None
    priority: Optional[EventPriority] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_all_day: Optional[bool] = None
    location: Optional[str] = None
    participants: Optional[List[str]] = None
    related_tasks: Optional[List[str]] = None
    is_recurring: Optional[bool] = None
    recurrence: Optional[Recurrence] = None

class EventResponse(EventCreate):
    id: str
    created_at: datetime
    updated_at: datetime

