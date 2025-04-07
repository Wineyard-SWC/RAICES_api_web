from fastapi import APIRouter, HTTPException
from typing import List
from firebase import userstories_ref
from models.userStorie_model import UserStories, UserStoriesResponse

router = APIRouter()

# Obtener userstories por ID de épicas
@router.get("/epics/{epic_id}/userstories", response_model=List[UserStoriesResponse])
def get_userstories_for_epic(epic_id: str):
    requirements = userstories_ref.where("epicRef", "==", epic_id).stream()
    return [UserStoriesResponse(id=req.id, **req.to_dict()) for req in requirements]

# Obtener una user story por ID
@router.get("/userstories/{story_id}", response_model=UserStoriesResponse)
def get_userstory(story_id: str):
    story_doc = userstories_ref.document(story_id).get()
    if not story_doc.exists:
        raise HTTPException(status_code=404, detail="User story not found")
    return UserStoriesResponse(id=story_doc.id, **story_doc.to_dict())

# Crear una nueva user story
@router.post("/userstories", response_model=UserStoriesResponse)
def create_userstory(story: UserStories):
    story_doc = userstories_ref.document()
    story_doc.set(story.dict())
    return UserStoriesResponse(id=story_doc.id, **story.dict())

# Actualizar una user story
@router.put("/userstories/{story_id}", response_model=UserStoriesResponse)
def update_userstory(story_id: str, story: UserStories):
    story_doc = userstories_ref.document(story_id)
    if not story_doc.get().exists:
        raise HTTPException(status_code=404, detail="User story not found")
    story_doc.update(story.dict())
    return UserStoriesResponse(id=story_id, **story.dict())

# Eliminar una user story
@router.delete("/userstories/{story_id}")
def delete_userstory(story_id: str):
    story_doc = userstories_ref.document(story_id)
    if not story_doc.get().exists:
        raise HTTPException(status_code=404, detail="User story not found")
    story_doc.delete()
    return {"message": "User story deleted successfully"}