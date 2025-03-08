from models.epic_models import Epic, EpicResponse  # Importamos los modelos de Epic
from models.req_models import Requirements
from firebase import epics_ref
from fastapi import APIRouter, HTTPException
from typing import List

# Inicializar FastAPI
router = APIRouter()

@router.post("/epics", response_model=EpicResponse)
async def create_epic(epic: Epic):
    # Crear un nuevo documento en la colección Epics
    doc = epics_ref.add(epic.dict())[1]
    
    # Retornar la épica creada con su ID
    return {**epic.dict(), "id": doc.id}

@router.get("/epics", response_model=List[EpicResponse])
async def get_all_epics():
    epics = epics_ref.stream()  # Obtener todas las épicas
    all_epics = []

    for doc in epics:
        epic_data = doc.to_dict()
        
        # Obtener las referencias de requerimientos
        related_reqs_refs = epic_data.get("RelatedReqs", [])

        # Resolver las referencias a requerimientos
        related_reqs = []
        for req_ref in related_reqs_refs:
            req_doc = req_ref.get()
            if req_doc.exists:
                req_data = req_doc.to_dict()
                id_req = req_data.get('IDReq', None)
                if id_req is not None:
                    related_reqs.append(Requirements(Desc=req_data['Desc'], IDReq=id_req, id=req_doc.id))

        all_epics.append({**epic_data, "id": doc.id, "RelatedReqs": related_reqs})

    return all_epics


@router.get("/epics/{epic_id}", response_model=EpicResponse)
async def get_epic_with_reqs(epic_id: str):
    doc = epics_ref.document(epic_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Epic not found")

    epic_data = doc.to_dict()
    
    # Obtener las referencias de requerimientos
    related_reqs_refs = epic_data.get("RelatedReqs", [])
    
    # Resolver las referencias a requerimientos
    related_reqs = []
    for req_ref in related_reqs_refs:
        req_doc = req_ref.get()  # Resolvemos la referencia
        if req_doc.exists:
            req_data = req_doc.to_dict()
            related_reqs.append(Requirements(Desc=req_data['Desc'], IDReq=req_data['IDReq'], id=req_doc.id))
        else:
            raise HTTPException(status_code=404, detail=f"Requirement {req_ref.id} not found")

    return {**epic_data, "id": doc.id, "RelatedReqs": related_reqs}

@router.put("/epics/{epic_id}", response_model=EpicResponse)
async def update_epic(epic_id: str, epic: Epic):
    doc_ref = epics_ref.document(epic_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Epic not found")

    # Actualizar el documento con los nuevos datos
    doc_ref.update(epic.dict())
    
    # Obtener la versión actualizada del documento
    updated_doc = doc_ref.get()
    return {**updated_doc.to_dict(), "id": updated_doc.id}

@router.delete("/epics/{epic_id}", response_model=EpicResponse)
async def delete_epic(epic_id: str):
    doc_ref = epics_ref.document(epic_id)
    doc = doc_ref.get()

    if not doc.exists:
        raise HTTPException(status_code=404, detail="Epic not found")

    # Eliminar el documento
    doc_ref.delete()

    # Retornar los datos de la épica eliminada
    return {**doc.to_dict(), "id": doc.id}
