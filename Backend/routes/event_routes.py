# event_routes.py
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from typing import List, Optional
from models.event_model import EventCreate, EventUpdate, EventResponse
from firebase_admin import firestore

router = APIRouter(tags=["Events"])
db = firestore.client()

@router.post("/projects/{project_id}/sprints/{sprint_id}/events", response_model=EventResponse)
async def create_event(
    project_id: str,
    sprint_id: str,
    event: EventCreate
):
    try:
        # Verificar que el sprint exista
        sprint_ref = db.collection("sprints").document(sprint_id)
        sprint = sprint_ref.get()
        if not sprint.exists or sprint.to_dict().get("project_id") != project_id:
            raise HTTPException(status_code=404, detail="Sprint not found")

        now = datetime.utcnow()
        event_data = event.dict()
        event_data.update({
            "created_at": now,
            "updated_at": now
        })

        # Crear el evento en Firestore
        event_ref = db.collection("events").document()
        event_ref.set(event_data)

        # Devolver el evento creado
        created_event = event_ref.get()
        return EventResponse(
            id=event_ref.id,
            **created_event.to_dict()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/projects/{project_id}/sprints/{sprint_id}/events", response_model=List[EventResponse])
async def get_events(
    project_id: str,
    sprint_id: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    try:
        # Verificar que el sprint exista
        sprint_ref = db.collection("sprints").document(sprint_id)
        sprint = sprint_ref.get()
        if not sprint.exists or sprint.to_dict().get("project_id") != project_id:
            raise HTTPException(status_code=404, detail="Sprint not found")

        # Construir la consulta base
        query = db.collection("events").where("sprint_id", "==", sprint_id)

        # Filtrar por rango de fechas si se proporciona
        if start_date and end_date:
            query = query.where("start_date", ">=", start_date)\
                         .where("start_date", "<=", end_date)
        elif start_date:
            query = query.where("start_date", ">=", start_date)
        elif end_date:
            query = query.where("start_date", "<=", end_date)

        # Ejecutar la consulta
        events = []
        for doc in query.stream():
            event_data = doc.to_dict()
            events.append(EventResponse(
                id=doc.id,
                **event_data
            ))

        return events
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/projects/{project_id}/sprints/{sprint_id}/events/{event_id}", response_model=EventResponse)
async def get_event(
    project_id: str,
    sprint_id: str,
    event_id: str
):
    try:
        # Verificar que el sprint exista
        sprint_ref = db.collection("sprints").document(sprint_id)
        sprint = sprint_ref.get()
        if not sprint.exists or sprint.to_dict().get("project_id") != project_id:
            raise HTTPException(status_code=404, detail="Sprint not found")

        # Obtener el evento
        event_ref = db.collection("events").document(event_id)
        event = event_ref.get()
        
        if not event.exists or event.to_dict().get("sprint_id") != sprint_id:
            raise HTTPException(status_code=404, detail="Event not found")

        return EventResponse(
            id=event_id,
            **event.to_dict()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/projects/{project_id}/sprints/{sprint_id}/events/{event_id}", response_model=EventResponse)
async def update_event(
    project_id: str,
    sprint_id: str,
    event_id: str,
    event: EventUpdate
):
    try:
        # Verificar que el sprint exista
        sprint_ref = db.collection("sprints").document(sprint_id)
        sprint = sprint_ref.get()
        if not sprint.exists or sprint.to_dict().get("project_id") != project_id:
            raise HTTPException(status_code=404, detail="Sprint not found")

        # Verificar que el evento exista
        event_ref = db.collection("events").document(event_id)
        existing_event = event_ref.get()
        if not existing_event.exists or existing_event.to_dict().get("sprint_id") != sprint_id:
            raise HTTPException(status_code=404, detail="Event not found")

        # Actualizar el evento
        update_data = event.dict(exclude_unset=True)
        update_data["updated_at"] = datetime.utcnow()
        
        event_ref.update(update_data)

        # Devolver el evento actualizado
        updated_event = event_ref.get()
        return EventResponse(
            id=event_id,
            **updated_event.to_dict()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/projects/{project_id}/sprints/{sprint_id}/events/{event_id}")
async def delete_event(
    project_id: str,
    sprint_id: str,
    event_id: str
):
    try:
        # Verificar que el sprint exista
        sprint_ref = db.collection("sprints").document(sprint_id)
        sprint = sprint_ref.get()
        if not sprint.exists or sprint.to_dict().get("project_id") != project_id:
            raise HTTPException(status_code=404, detail="Sprint not found")

        # Verificar que el evento exista
        event_ref = db.collection("events").document(event_id)
        event = event_ref.get()
        if not event.exists or event.to_dict().get("sprint_id") != sprint_id:
            raise HTTPException(status_code=404, detail="Event not found")

        # Eliminar el evento
        event_ref.delete()
        return {"message": "Event deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))