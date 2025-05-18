from pydantic import BaseModel, Field

class PermissionCreate(BaseModel):
    bit: int = Field(..., ge=0, le=31, description="Bit position (0…31) for mask")
    name: str = Field(..., description="Human-readable name, e.g. 'Project Administration'")
    description: str = Field(..., description="Detailed description in English")

class PermissionResponse(PermissionCreate):
    id: str = Field(..., description="Firestore document ID assigned to this permission")
