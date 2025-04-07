from pydantic import BaseModel

class Epics(BaseModel):
    idTitle: str
    title: str
    description: str

class EpicsResponse(Epics):
    id: str
