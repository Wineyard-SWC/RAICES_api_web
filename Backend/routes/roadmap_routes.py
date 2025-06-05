from fastapi import APIRouter, HTTPException, status, Depends
from firebase_admin import firestore
from firebase import db, roadmap_ref
from models.roadmap_model import (
    Roadmap, 
    RoadmapCreate, 
    RoadmapUpdate, 
    RoadmapResponse, 
    RoadmapSummary,
    RoadmapPhase
)
from typing import List, Optional
from datetime import datetime
import uuid

router = APIRouter(tags=["Roadmap"])

def calculate_roadmap_stats(phases: List[RoadmapPhase]) -> tuple[int, int]:
    """Calcula estadísticas del roadmap"""
    phase_count = len(phases)
    total_items = sum(len(phase.items) for phase in phases)
    return phase_count, total_items

def get_roadmap_by_id(roadmap_id: str) -> Optional[dict]:
    """Obtiene un roadmap por ID"""
    try:
        doc = roadmap_ref.document(roadmap_id).get()
        if doc.exists:
            return {"id": doc.id, **doc.to_dict()}
        return None
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching roadmap: {str(e)}"
        )

def resolve_roadmap_phases(roadmap_data: dict) -> List[RoadmapPhase]:
    """Resuelve las phases de un roadmap, incluyendo lógica de copias"""
    phases = roadmap_data.get("phases", [])
    
    if (roadmap_data.get("isDuplicate", False) and 
        not roadmap_data.get("isModified", True) and 
        roadmap_data.get("sourceRoadmapId")):
        
        source_roadmap = get_roadmap_by_id(roadmap_data["sourceRoadmapId"])
        if source_roadmap:
            phases = source_roadmap.get("phases", phases)
    
    return [RoadmapPhase(**phase) if isinstance(phase, dict) else phase for phase in phases]

@router.get("/projects/{project_id}/roadmaps", response_model=List[RoadmapResponse])
async def get_roadmaps_from_project(project_id: str):
    """Obtiene todos los roadmaps de un proyecto"""
    try:
        # Buscar roadmaps por projectId (ajusta el campo según tu esquema)
        query = roadmap_ref.where("projectId", "==", project_id)
        roadmaps = query.stream()
        
        result = []
        for roadmap_doc in roadmaps:
            roadmap_data = {"id": roadmap_doc.id, **roadmap_doc.to_dict()}
            
            # Resolver phases (incluyendo lógica de copias)
            phases = resolve_roadmap_phases(roadmap_data)
            
            # Calcular estadísticas
            phase_count, total_items = calculate_roadmap_stats(phases)
            
            # Crear objeto de respuesta
            roadmap_response = RoadmapResponse(
                id=roadmap_data["id"],
                name=roadmap_data["name"],
                description=roadmap_data.get("description"),
                phases=phases,
                sourceRoadmapId=roadmap_data.get("sourceRoadmapId"),
                isDuplicate=roadmap_data.get("isDuplicate", False),
                isModified=roadmap_data.get("isModified", True),
                createdAt=roadmap_data.get("createdAt", ""),
                updatedAt=roadmap_data.get("updatedAt", ""),
                projectId=roadmap_data["projectId"],
                phaseCount=phase_count,
                totalItems=total_items
            )
            result.append(roadmap_response)
        
        # Ordenar por fecha de actualización (más recientes primero)
        result.sort(key=lambda x: x.updatedAt, reverse=True)
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching roadmaps: {str(e)}"
        )

@router.post("/projects/roadmaps", response_model=RoadmapResponse)
async def create_roadmap(roadmap_data: RoadmapCreate):
    """Crea un nuevo roadmap"""
    try:
        
        # Generar ID único
        roadmap_id = str(uuid.uuid4())
        current_time = datetime.utcnow().isoformat()
        
        # Crear objeto roadmap
        roadmap = Roadmap(
            id=roadmap_id,
            name=roadmap_data.name,
            description=roadmap_data.description,
            phases=roadmap_data.phases,
            sourceRoadmapId=roadmap_data.sourceRoadmapId,
            isDuplicate=roadmap_data.isDuplicate,
            isModified=True if not roadmap_data.isDuplicate else False,
            createdAt=current_time,
            updatedAt=current_time,
            projectId=roadmap_data.projectId
        )
        
        # Si es una copia, validar que el roadmap original existe
        if roadmap.isDuplicate and roadmap.sourceRoadmapId:
            source_roadmap = get_roadmap_by_id(roadmap.sourceRoadmapId)
            if not source_roadmap:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Source roadmap not found"
                )
        
        roadmap_dict = roadmap.dict()
        roadmap_dict.pop("id", None) 
        
        roadmap_ref.document(roadmap_id).set(roadmap_dict)
        
        phase_count, total_items = calculate_roadmap_stats(roadmap.phases)
        
        # Crear respuesta
        return RoadmapResponse(
            id=roadmap_id,
            name=roadmap.name,
            description=roadmap.description,
            phases=roadmap.phases,
            sourceRoadmapId=roadmap.sourceRoadmapId,
            isDuplicate=roadmap.isDuplicate,
            isModified=roadmap.isModified,
            createdAt=roadmap.createdAt,
            updatedAt=roadmap.updatedAt,
            projectId=roadmap.projectId,
            phaseCount=phase_count,
            totalItems=total_items
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating roadmap: {str(e)}"
        )

@router.put("/projects/roadmaps/{roadmap_id}", response_model=RoadmapResponse)
async def update_roadmap(roadmap_id: str, roadmap_data: RoadmapUpdate):
    """Actualiza un roadmap existente"""
    try:
        existing_roadmap = get_roadmap_by_id(roadmap_id)
        if not existing_roadmap:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Roadmap not found"
            )
        
        update_data = {}
        
        if roadmap_data.name is not None:
            update_data["name"] = roadmap_data.name
            
        if roadmap_data.description is not None:
            update_data["description"] = roadmap_data.description
            
        if roadmap_data.phases is not None:
            update_data["phases"] = [phase.dict() for phase in roadmap_data.phases]
            if existing_roadmap.get("isDuplicate", False):
                update_data["isModified"] = True
                
        if roadmap_data.isModified is not None:
            update_data["isModified"] = roadmap_data.isModified
        
        update_data["updatedAt"] = datetime.utcnow().isoformat()
        
        roadmap_ref.document(roadmap_id).update(update_data)
        
        updated_roadmap = get_roadmap_by_id(roadmap_id)
        if not updated_roadmap:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error retrieving updated roadmap"
            )
        
        phases = resolve_roadmap_phases(updated_roadmap)
        
        phase_count, total_items = calculate_roadmap_stats(phases)
        
        # Crear respuesta
        return RoadmapResponse(
            id=updated_roadmap["id"],
            name=updated_roadmap["name"],
            description=updated_roadmap.get("description"),
            phases=phases,
            sourceRoadmapId=updated_roadmap.get("sourceRoadmapId"),
            isDuplicate=updated_roadmap.get("isDuplicate", False),
            isModified=updated_roadmap.get("isModified", True),
            createdAt=updated_roadmap.get("createdAt", ""),
            updatedAt=updated_roadmap.get("updatedAt", ""),
            projectId=updated_roadmap["projectId"],
            phaseCount=phase_count,
            totalItems=total_items
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating roadmap: {str(e)}"
        )

@router.delete("/projects/roadmaps/{roadmap_id}")
async def remove_roadmap_from_project(roadmap_id: str):
    """Elimina un roadmap"""
    try:
        # Verificar que el roadmap existe
        existing_roadmap = get_roadmap_by_id(roadmap_id)
        if not existing_roadmap:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Roadmap not found"
            )
        
        query = roadmap_ref.where("sourceRoadmapId", "==", roadmap_id)
        dependent_roadmaps = list(query.stream())
        
        if dependent_roadmaps:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete roadmap. {len(dependent_roadmaps)} copies depend on it."
            )
        
        # Eliminar el roadmap
        roadmap_ref.document(roadmap_id).delete()
        
        return {"message": "Roadmap deleted successfully", "id": roadmap_id}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting roadmap: {str(e)}"
        )

@router.get("/projects/{project_id}/roadmaps/summary", response_model=List[RoadmapSummary])
async def get_roadmaps_summary(project_id: str):
    """Obtiene un resumen de los roadmaps de un proyecto (para listas)"""
    try:
        query = roadmap_ref.where("projectId", "==", project_id)
        roadmaps = query.stream()
        
        result = []
        for roadmap_doc in roadmaps:
            roadmap_data = {"id": roadmap_doc.id, **roadmap_doc.to_dict()}
            
            phases = resolve_roadmap_phases(roadmap_data)
            phase_count, total_items = calculate_roadmap_stats(phases)
            
            summary = RoadmapSummary(
                id=roadmap_data["id"],
                name=roadmap_data["name"],
                description=roadmap_data.get("description"),
                phaseCount=phase_count,
                totalItems=total_items,
                isDuplicate=roadmap_data.get("isDuplicate", False),
                isModified=roadmap_data.get("isModified", True),
                createdAt=roadmap_data.get("createdAt", ""),
                updatedAt=roadmap_data.get("updatedAt", "")
            )
            result.append(summary)
        
        result.sort(key=lambda x: x.updatedAt, reverse=True)
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching roadmaps summary: {str(e)}"
        )

@router.get("/roadmaps/{roadmap_id}", response_model=RoadmapResponse)
async def get_roadmap_by_id_endpoint(roadmap_id: str):
    """Obtiene un roadmap específico por ID"""
    try:
        roadmap_data = get_roadmap_by_id(roadmap_id)
        if not roadmap_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Roadmap not found"
            )
        
        # Resolver phases
        phases = resolve_roadmap_phases(roadmap_data)
        
        # Calcular estadísticas
        phase_count, total_items = calculate_roadmap_stats(phases)
        
        return RoadmapResponse(
            id=roadmap_data["id"],
            name=roadmap_data["name"],
            description=roadmap_data.get("description"),
            phases=phases,
            sourceRoadmapId=roadmap_data.get("sourceRoadmapId"),
            isDuplicate=roadmap_data.get("isDuplicate", False),
            isModified=roadmap_data.get("isModified", True),
            createdAt=roadmap_data.get("createdAt", ""),
            updatedAt=roadmap_data.get("updatedAt", ""),
            projectId=roadmap_data["projectId"],
            phaseCount=phase_count,
            totalItems=total_items
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching roadmap: {str(e)}"
        )