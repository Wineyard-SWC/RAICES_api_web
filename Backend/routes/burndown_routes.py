from fastapi import APIRouter
from firebase_admin import firestore
from datetime import datetime
from models.task_model import GraphicsRequest
router = APIRouter()
db = firestore.client()

def to_date(date_time):
    return date_time.date() if date_time else None

@router.post("/api/burndown")
async def get_burndown_data(payload:GraphicsRequest):
    projectId=payload.projectId,
    tasks=payload.tasks or []

    now = datetime.now().date()

    sprints_snapshots = db.collection("sprints").where("project_id", "==", projectId).stream()

    active_sprint = None

    for snap in sprints_snapshots:
        data = snap.to_dict()
        start = data.get("start_date")
        end = data.get("end_date")
        start_date = to_date(start)
        end_date = to_date(end)

        if start_date and end_date and start_date <= now <= end_date:
            data["duration_days"] = (end_date - start_date).days + 1
            active_sprint = data
            break
    
    if not active_sprint:
        return {"error": "No active sprint found for this project"}

    if not tasks:
        # Leer solo los campos necesarios
        tasks_snapshots = db.collection("tasks")\
            .where("project_id", "==", projectId)\
            .select("story_points", "status_khanban")\
            .stream()
    else:
        tasks_snapshots = tasks

    total_sp = 0
    done_sp = 0

    if tasks_snapshots:    
        for task in tasks_snapshots:
            data = task.to_dict()
            sp = data.get("story_points", 0)
            if isinstance(sp, int):
                total_sp += sp
                if data.get("status_khanban", "").strip().lower() == "done":
                    done_sp += sp

    # Agregar al sprint activo
    active_sprint["total_story_points"] = total_sp
    active_sprint["done_story_points"] = done_sp
    active_sprint["remaining_story_points"] = max(total_sp - done_sp, 0)

    return active_sprint