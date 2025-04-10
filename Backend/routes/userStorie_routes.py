from firebase import db
from fastapi import APIRouter, HTTPException
from typing import List
from firebase import userstories_ref, epics_ref
from models.userStorie_model import UserStory, UserStoryResponse
from typing import Optional

router = APIRouter()

@router.post("/projects/{project_id}/userstories/batch", response_model=List[UserStoryResponse])
def create_userstories_batch(
    project_id: str,
    userstories: List[UserStory],
    epic_id: Optional[str] = None  # Opcional: asignar todos a la misma épica
):

    batch = db.batch()  
    created_stories = []
    
    # Verificar épica si se especificó
    if epic_id:
        epic_query = epics_ref.where("idTitle", "==", epic_id)\
                            .where("projectRef", "==", project_id)\
                            .limit(1).stream()
        if not list(epic_query):
            raise HTTPException(status_code=404, detail="Epic not found")

    for story in userstories:
        if story.projectRef != project_id:
            raise HTTPException(status_code=400, detail=f"ProjectRef mismatch in user story {story.idTitle}")
        
        # Asignar épica si se especificó
        if epic_id:
            story.epicRef = epic_id
        
        # Verificar si ya existe
        existing_query = userstories_ref.where("idTitle", "==", story.idTitle)\
                                      .where("projectRef", "==", project_id)\
                                      .limit(1).stream()
        
        existing = list(existing_query)
        
        if existing:
            # Actualizar existente
            story_doc = userstories_ref.document(existing[0].id)
            batch.update(story_doc, story.dict())
            created_stories.append({"id": story_doc.id, **story.dict()})
        else:
            # Crear nuevo
            new_doc = userstories_ref.document()
            batch.set(new_doc, story.dict())
            created_stories.append({"id": new_doc.id, **story.dict()})
    
    batch.commit()
    return created_stories


# Obtener todas las user stories de un proyecto
@router.get("/projects/{project_id}/userstories", response_model=List[UserStoryResponse])
def get_project_userstories(project_id: str):
    userstories = userstories_ref.where("projectRef", "==", project_id).stream()
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
    

# Eliminar user story
@router.delete("/projects/{project_id}/userstories/{story_id}")
def delete_userstory(project_id: str, story_id: str):
    story_query = userstories_ref.where("idTitle", "==", story_id)\
                                .where("projectRef", "==", project_id)\
                                .limit(1).stream()
    story_list = list(story_query)
    if not story_list:
        raise HTTPException(status_code=404, detail="User story not found")
    
    userstories_ref.document(story_list[0].id).delete()
    return {"message": "User story deleted successfully"}