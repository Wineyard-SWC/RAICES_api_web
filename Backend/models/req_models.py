from pydantic import BaseModel

# Requerimientos
class Requirements(BaseModel):
    Desc: str 
    IDReq: str 

class ReqResponse(Requirements):
    id: str  
