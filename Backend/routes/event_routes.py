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
    
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from typing import List, Optional
from models.event_model import EventCreate, EventUpdate, EventResponse
from firebase_admin import firestore
import pytz  # Add this import for timezone handling

@router.get("/projects/{project_id}/events/today", response_model=List[EventResponse])
async def get_project_today_events(project_id: str):
    """
    Get all events scheduled for today for a specific project.
    Uses UTC-6 timezone (Central Time) to determine "today".
    
    Parameters:
    - project_id: The ID of the project
    
    Returns:
    - List of events that start today for the given project
    """
    try:
        # Verify project exists
        project_ref = db.collection("projects").document(project_id)
        project = project_ref.get()
        if not project.exists:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get today's date range in UTC-6 timezone
        central_tz = pytz.timezone('America/Chicago')  # UTC-6
        now_utc = datetime.utcnow().replace(tzinfo=pytz.UTC)
        now_central = now_utc.astimezone(central_tz)
        
        # Start of day in UTC-6, then convert back to UTC for comparison
        today_central = now_central.replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_central = today_central.replace(hour=23, minute=59, second=59)
        
        # Convert back to UTC for proper comparison with Firestore timestamps
        today_utc = today_central.astimezone(pytz.UTC)
        tomorrow_utc = tomorrow_central.astimezone(pytz.UTC)
        
        # Get ALL events from Firestore
        events_query = db.collection("events").stream()

        # Check if the query returned any documents
        if not events_query:
            raise HTTPException(status_code=404, detail="No events found")
                
        # Process and filter by project and date in Python code
        events = []
        for doc in events_query:
            event_data = doc.to_dict()
            
            # First check if the event belongs to any sprint of the project
            event_sprint_id = event_data.get("sprint_id")
            if not event_sprint_id:
                continue
                                
            # Now check if the event is today in UTC-6
            event_start = event_data.get("start_date")
            
            # Add timezone info if it's naive
            if event_start and not event_start.tzinfo:
                event_start = event_start.replace(tzinfo=pytz.UTC)
            
            # Only include if start_date is within today's range in UTC-6
            if event_start and today_utc <= event_start <= tomorrow_utc:
                events.append(EventResponse(
                    id=doc.id,
                    **event_data
                ))
        
        return events
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.delete("/events/{event_id}")
async def delete_event_by_id(event_id: str):
    """
    Delete an event using only its ID.
    
    Parameters:
    - event_id: The ID of the event to delete
    
    Returns:
    - Success message
    """
    try:
        # Verify that the event exists
        event_ref = db.collection("events").document(event_id)
        event = event_ref.get()
        
        if not event.exists:
            raise HTTPException(status_code=404, detail=f"Event with ID {event_id} not found")

        # Delete the event
        event_ref.delete()
        
        return {"message": f"Event {event_id} successfully deleted"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))