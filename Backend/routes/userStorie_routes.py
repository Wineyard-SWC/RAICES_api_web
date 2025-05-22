from firebase import db
from fastapi import APIRouter, HTTPException
from typing import List
from firebase import userstories_ref, epics_ref, projects_ref
from firebase_admin import firestore
from models.userStorie_model import UserStory, UserStoryResponse,StatusUpdate
from typing import Optional
from datetime import datetime
from helpers import delete_user_story_and_related

router = APIRouter(tags=["UserStories"])

@router.post("/projects/{project_id}/userstories/batch", response_model=List[UserStoryResponse])
def create_userstories_batch(
    project_id: str,
    userstories: List[UserStory],
    epic_id: Optional[str] = None,  
    archive_missing: bool = True    
):
    project_ref = projects_ref.document(project_id)
    project = project_ref.get()
    
    if not project.exists:
        raise HTTPException(
            status_code=404,
            detail=f"Project with ID {project_id} not found"
        )

    # Verificar épica si se especificó
    if epic_id:
        epic_query = epics_ref.where("idTitle", "==", epic_id)\
                            .where("projectRef", "==", project_id)\
                            .limit(1).stream()
        if not list(epic_query):
            raise HTTPException(status_code=404, detail="Epic not found")
    
    # Obtener historias de usuario existentes para este proyecto
    existing_stories = {
        doc.to_dict()["idTitle"]: doc.reference 
        for doc in userstories_ref.where("projectRef", "==", project_id).stream()
    }
    
    # Seguimiento de las historias que estamos actualizando
    updated_story_ids = set()
    batch = db.batch()
    created_stories = []
    
    # Actualizar o crear historias de usuario
    for story in userstories:
        if story.projectRef != project_id:
            raise HTTPException(status_code=400, detail=f"ProjectRef mismatch in user story {story.idTitle}")
        
        # Asignar épica si se especificó
        if epic_id:
            story.epicRef = epic_id
        
        # Preparar datos con status y timestamp
        story_dict = story.dict() if hasattr(story, 'dict') else story.model_dump(exclude_unset=True, exclude_none=True)
        story_dict["status"] = "active"  # Marcar como activa
        story_dict["lastUpdated"] = firestore.SERVER_TIMESTAMP
        
        # Actualizar o crear
        if story.idTitle in existing_stories:
            # Actualizar existente
            story_ref_doc = existing_stories[story.idTitle]
            batch.update(story_ref_doc, story_dict)
            created_stories.append(UserStoryResponse(id=story_ref_doc.id, **story_dict))
        else:
            # Crear nueva
            new_doc = userstories_ref.document()
            batch.set(new_doc, story_dict)
            created_stories.append(UserStoryResponse(id=new_doc.id, **story_dict))
        
        # Marcar esta historia como actualizada
        updated_story_ids.add(story.idTitle)
    
    if archive_missing:
        for story_id, story_ref_doc in existing_stories.items():
            if story_id not in updated_story_ids:
                batch.update(story_ref_doc, {
                    "status": "archived",
                    "lastUpdated": firestore.SERVER_TIMESTAMP
                })
    
    # Confirmar todos los cambios
    batch.commit()
    
    return created_stories


# Obtener todas las user stories de un proyecto
@router.get("/projects/{project_id}/userstories", response_model=List[UserStoryResponse])
def get_project_userstories(
    project_id: str,
    include_archived: bool = False  
):
    query = userstories_ref.where("projectRef", "==", project_id)
    
    if not include_archived:
        query = query.where("status", "==", "active")
    
    userstories = query.stream()
    return [UserStoryResponse(id=story.id, **story.to_dict()) for story in userstories]



# Obtener una user story específica
@router.get("/projects/{project_id}/userstories/{story_id}", response_model=UserStoryResponse)
def get_userstory(project_id: str, story_id: str):  # story_id es el idTitle (ej. US-001)
    story_query = userstories_ref.where("idTitle", "==", story_id)\
                               .where("projectRef", "==", project_id)\
                               .limit(1).stream()
    story_list = list(story_query)
    if not story_list:
        raise HTTPException(status_code=404, detail="User story not found")
    story = story_list[0]
    return UserStoryResponse(id=story.id, **story.to_dict())


# Obtener user stories de una épica específica
@router.get("/projects/{project_id}/epics/{epic_id}/userstories", response_model=List[UserStoryResponse])
def get_epic_userstories(project_id: str, epic_id: str):
    # Verificar que la épica existe
    epic_query = epics_ref.where("idTitle", "==", epic_id)\
                         .where("projectRef", "==", project_id)\
                         .limit(1).stream()
    if not list(epic_query):
        raise HTTPException(status_code=404, detail="Epic not found")
    
    userstories = userstories_ref.where("epicRef", "==", epic_id)\
                                .where("projectRef", "==", project_id)\
                                .stream()
    return [UserStoryResponse(id=story.id, **story.to_dict()) for story in userstories]


# Asignar user story a una épica
@router.put("/projects/{project_id}/userstories/{story_id}/assign-to-epic/{epic_id}", response_model=UserStoryResponse)
def assign_userstory_to_epic(
    project_id: str,
    story_id: str,  # idTitle de la user story (ej. US-001)
    epic_id: str  # idTitle de la épica (ej. EPIC-001)
):
    # Verificar que la épica existe
    epic_query = epics_ref.where("idTitle", "==", epic_id)\
                         .where("projectRef", "==", project_id)\
                         .limit(1).stream()
    if not list(epic_query):
        raise HTTPException(status_code=404, detail="Epic not found")
    
    # Buscar user story
    story_query = userstories_ref.where("idTitle", "==", story_id)\
                                .where("projectRef", "==", project_id)\
                                .limit(1).stream()
    story_list = list(story_query)
    if not story_list:
        raise HTTPException(status_code=404, detail="User story not found")
    
    # Actualizar
    story_doc = userstories_ref.document(story_list[0].id)
    story_doc.update({"epicRef": epic_id})
    
    updated_story = story_doc.get().to_dict()
    return UserStoryResponse(id=story_doc.id, **updated_story)


# Crear o actualizar user story (upsert)
@router.post("/projects/{project_id}/userstories", response_model=UserStoryResponse)
def upsert_userstory(project_id: str, story: UserStory):
    # Validar coherencia del projectRef
    if story.projectRef != project_id:
        raise HTTPException(status_code=400, detail="ProjectRef mismatch")
    
    # Si tiene epicRef, validar que la épica existe
    if story.epicRef:
        epic_query = epics_ref.where("idTitle", "==", story.epicRef)\
                             .where("projectRef", "==", project_id)\
                             .limit(1).stream()
        if not list(epic_query):
            raise HTTPException(status_code=404, detail="Epic not found")
    
    # Buscar si ya existe
    existing_query = userstories_ref.where("idTitle", "==", story.idTitle)\
                                  .where("projectRef", "==", project_id)\
                                  .limit(1).stream()
    existing = list(existing_query)
    
    if existing:
        # Actualizar
        story_doc = userstories_ref.document(existing[0].id)
        story_doc.update(story.dict())
        return UserStoryResponse(id=story_doc.id, **story.dict())
    else:
        # Crear nuevo
        new_doc = userstories_ref.document()
        new_doc.set(story.dict())
        return UserStoryResponse(id=new_doc.id, **story.dict())
    

# 7) Actualizar una task existente
@router.put(
    "/projects/{project_id}/userstories/{story_id}",
    response_model=UserStoryResponse
)
def update_story(project_id: str, story_id: str, t: UserStory):
    ref = userstories_ref.document(story_id)
    snap = ref.get()
    if not snap.exists or snap.get("projectRef") != project_id:
        raise HTTPException(404, "Story not found")

    data = t.dict(exclude_unset=True, exclude_none=True)
    ref.update(data)

    updated = ref.get().to_dict() or {}

    updated_copy = {k: v for k, v in updated.items() 
                    if k not in ['id']}
   

    return UserStoryResponse(
        id=story_id,
        **updated_copy
    )




# Eliminar user story
@router.delete("/projects/{project_id}/userstories/{story_id}")
def delete_userstory(project_id: str, story_id: str):
    try:
        delete_user_story_and_related(project_id, story_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"message": "User story, tasks and related bugs deleted successfully"}




# 9) Agregar un comentario a una task
@router.post("/projects/{project_id}/userstories/{story_id}/comments")
def add_comment(project_id: str, story_id: str, comment: dict):
    ref = userstories_ref.document(story_id)
    snap = ref.get()
    if not snap.exists or snap.get("projectRef") != project_id:
        raise HTTPException(404, "Story not found")

    comment["timestamp"] = datetime.utcnow().isoformat()
    ref.update({ "comments": firestore.ArrayUnion([comment]) })

    return { "message": "Comment added successfully" }


@router.delete("/projects/{project_id}/userstories/{story_id}/comments/{comment_id}")
def delete_comment(project_id: str, story_id: str, comment_id: str):
    doc_ref = userstories_ref.document(story_id)
    doc = doc_ref.get()
    if not doc.exists or doc.get("projectRef") != project_id:
        raise HTTPException(404, "Story not found")
    
    data = doc.to_dict()
    updated_comments = [c for c in data.get("comments", []) if c["id"] != comment_id]
    doc_ref.update({"comments": updated_comments})
    return {"message": "Comment deleted"}


@router.patch("/projects/{project_id}/userstories/{story_id}/status")
def update_story_status(project_id: str, story_id: str, payload: StatusUpdate):
    # Validar que el proyecto exista
    if not projects_ref.document(project_id).get().exists:
        raise HTTPException(404, "Project not found")

    story_doc = userstories_ref.document(story_id).get()
    if not story_doc.exists or story_doc.get("projectRef") != project_id:
        raise HTTPException(404, "Story not found")

    userstories_ref.document(story_id).update({
        "status_khanban": payload.status_khanban
    })

    return {"message": f"Story {story_id} status updated to {payload.status_khanban}"}