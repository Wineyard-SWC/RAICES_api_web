from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class RoadmapPhase(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    color: Optional[str] = "#FFFFFF"
    position: Dict[str, float] = Field(default_factory=lambda: {"x": 0, "y": 0})
    items: List[str] = Field(default_factory=list) 
    itemCount: int = 0

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class RoadmapCreate(BaseModel):
    """Modelo para crear un roadmap"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    phases: List[RoadmapPhase] = Field(default_factory=list)
    projectId: str = Field(..., min_length=1)
    
    # Campos para manejo de copias
    sourceRoadmapId: Optional[str] = None
    isDuplicate: bool = False
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class RoadmapUpdate(BaseModel):
    """Modelo para actualizar un roadmap"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    phases: Optional[List[RoadmapPhase]] = None
    isModified: Optional[bool] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class Roadmap(BaseModel):
    """Modelo completo del roadmap (DatabaseRoadmap en frontend)"""
    id: Optional[str] = None  
    name: str = Field(..., min_length=1, max_length=1000)
    description: Optional[str] = Field(None, max_length=1000)
    phases: List[RoadmapPhase] = Field(default_factory=list)
    
    # Campos para manejo de copias
    sourceRoadmapId: Optional[str] = None
    isDuplicate: bool = False
    isModified: bool = True
    
    # Metadatos
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None
    projectId: str = Field(..., min_length=1)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class RoadmapResponse(BaseModel):
    """Modelo de respuesta para roadmaps"""
    id: str
    name: str
    description: Optional[str] = None
    phases: List[RoadmapPhase] = Field(default_factory=list)
    
    # Campos para manejo de copias
    sourceRoadmapId: Optional[str] = None
    isDuplicate: bool = False
    isModified: bool = True
    
    # Metadatos
    createdAt: str
    updatedAt: str
    projectId: str
    
    # Campos adicionales para la respuesta
    phaseCount: int = 0
    totalItems: int = 0
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class RoadmapSummary(BaseModel):
    """Modelo resumido para listas de roadmaps"""
    id: str
    name: str
    description: Optional[str] = None
    phaseCount: int = 0
    totalItems: int = 0
    isDuplicate: bool = False
    isModified: bool = True
    createdAt: str
    updatedAt: str
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }