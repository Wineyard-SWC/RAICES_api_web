from fastapi import APIRouter, HTTPException
from typing import List,Dict,Any,Tuple
from firebase import bugs_ref,projects_ref
from models.bug_model import Bug,StatusUpdate,BugBase
from firebase_admin import firestore
from datetime import datetime


router = APIRouter(tags=["Bugs"])

def safe_iso(dt):
    if isinstance(dt, datetime):
        return dt.isoformat()
    if hasattr(dt, "isoformat"):
        return dt.isoformat()
    if isinstance(dt, str):
        return dt
    return ""

def convert_assignee_format(data: Dict[str, Any]) -> List[Tuple[str, str]]:
    assigned_users = []
    if "assignees" in data and data["assignees"]:
        for user in data["assignees"]:
            if isinstance(user, dict) and "users" in user:
                uid, uname = user["users"]
                assigned_users.append((uid, uname))
    return assigned_users


# Obtener todos los bugs de un proyecto
@router.get("/bugs/project/{project_id}", response_model=List[Bug])
def get_bugs_by_project(project_id: str):
    if not projects_ref.document(project_id).get().exists:
        raise HTTPException(status_code=404, detail="Project not found")

    docs = bugs_ref.where("projectId", "==", project_id).stream()
    results = []

    for d in docs:
        raw = d.to_dict() or {}
        
        for key in ["id", "createdAt", "modifiedAt", "assignees"]:
            raw.pop(key, None)

        assigned = convert_assignee_format(d.to_dict())

        results.append(Bug(
            id=d.id,
            assignees=[{"users": a} for a in assigned],
            createdAt=safe_iso(d.get("createdAt")),
            modifiedAt=safe_iso(d.get("modifiedAt")),
            **raw
        ))

    return results

# Obtener un bug por ID
@router.get("/bugs/{bug_id}", response_model=Bug)
def get_bug(bug_id: str):
    doc = bugs_ref.document(bug_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Bug not found")
    
    raw = doc.to_dict()
    assigned = convert_assignee_format(raw)

    raw.pop("id", None)
    raw.pop("createdAt", None)
    raw.pop("modifiedAt", None)
    raw.pop("assignees", None)

    return Bug(
        id=doc.id,
        assignees=[{"users": a} for a in assigned],
        modifiedAt=safe_iso(raw.get("modifiedAt")),
        createdAt=safe_iso(raw.get("createdAt")),
        **raw
    )
# Crear un bug
@router.post("/bugs", response_model=Bug)
def create_bug(bug: Bug):
    if not projects_ref.document(bug.projectId).get().exists:
        raise HTTPException(404, "Project not found")

    ref = bugs_ref.document(bug.id)
    if ref.get().exists:
        raise HTTPException(400, "Bug already exists")

    data = bug.dict(exclude_unset=True)
    data["createdAt"] = firestore.SERVER_TIMESTAMP
    data["modifiedAt"] = firestore.SERVER_TIMESTAMP

    ref.set(data)
    saved = ref.get().to_dict()

    saved["id"] = bug.id    
    saved["createdAt"] = saved["createdAt"].isoformat()
    saved["modifiedAt"] = saved["modifiedAt"].isoformat()
    return Bug(**saved)

# Actualizar un bug
@router.put("/bugs/{bug_id}", response_model=Bug)
def update_bug(bug_id: str, bug: BugBase):
    ref = bugs_ref.document(bug_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Bug not found")

    data = bug.dict(exclude_unset=True, exclude_none=True)
    data["modifiedAt"] = firestore.SERVER_TIMESTAMP

    ref.update(data)
    updated = ref.get().to_dict() or {}
    assigned = convert_assignee_format(updated)
    
    for key in ["id", "modifiedAt", "createdAt", "assignees"]:
        updated.pop(key, None)

    return Bug(
        id=bug_id,
        assignees=[{"users": a} for a in assigned],
        modifiedAt=safe_iso(updated.get("modifiedAt")),
        createdAt=safe_iso(updated.get("createdAt")),
        **updated
    )

# Eliminar un bug
@router.delete("/bugs/{bug_id}")
def delete_bug(bug_id: str):
    ref = bugs_ref.document(bug_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Bug not found")
    
    ref.delete()
    return {"message": "Bug deleted successfully"}



@router.patch("/projects/{project_id}/bugs/{bug_id}/status")
def update_story_status(project_id: str, bug_id: str, payload: StatusUpdate):
    # Validar que el proyecto exista
    if not projects_ref.document(project_id).get().exists:
        raise HTTPException(404, "Project not found")

    bug_doc = bugs_ref.document(bug_id).get()
    if not bug_doc.exists or bug_doc.get("projectId") != project_id:
        raise HTTPException(404, "Bug not found")

    bugs_ref.document(bug_id).update({
        "status_khanban": payload.status_khanban
    })

    return {"message": f"Story {bug_id} status updated to {payload.status_khanban}"}