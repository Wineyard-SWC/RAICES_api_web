from fastapi import APIRouter
from firebase_admin import firestore
from datetime import datetime

router = APIRouter()
db = firestore.client()

def to_date(date_time):
    return date_time.date() if date_time else None

@router.get("/api/velocitytrend")
async def get_velocity_trend(projectId: str):
    now = datetime.now().date()
    
    # Obtener sprints del proyecto
    sprints_ref = db.collection("sprints").where("project_id", "==", projectId)
    sprints = list(sprints_ref.stream())

    active_sprint = None

    for sprint in sprints:
        sprint_data = sprint.to_dict()
        start = to_date(sprint_data.get("start_date"))
        end = to_date(sprint_data.get("end_date"))

        if start and end and start <= now <= end:
            active_sprint = sprint_data
            break

    if not active_sprint:
        return {"error": "No active sprint found for this project"}

    project_sprints = [
        (sprint.id, sprint.to_dict()) for sprint in sprints
        if sprint.to_dict().get("project_id") == projectId
    ]

    num_sprints = len(project_sprints)

    # Obtener tareas del proyecto
    tasks_ref = db.collection("tasks").where("project_id", "==", projectId)
    tasks = list(tasks_ref.stream())

    total_story_points = 0
    done_story_points = 0

    for task in tasks:
        task_data = task.to_dict()
        sp = task_data.get("story_points", 0)
        if isinstance(sp, int):
            total_story_points += sp
            if task_data.get("status_khanban", "").lower() == "done":
                done_story_points += sp

    planned_per_sprint = round(total_story_points / num_sprints, 2) if num_sprints > 0 else 0

    # Todos los sprints muestran el mismo progreso acumulado (done_story_points)
    sprint_velocity = []
    for sprint_id, sprint_data in project_sprints:
        sprint_name = sprint_data.get("name") or f"Sprint {sprint_data.get('number', sprint_id[:6])}"
        sprint_velocity.append({
            "sprint": sprint_name,
            "Planned": planned_per_sprint,
            "Actual": done_story_points
        })

    return sprint_velocity