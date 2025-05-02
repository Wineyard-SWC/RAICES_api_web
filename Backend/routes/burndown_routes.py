from fastapi import APIRouter
from firebase_admin import firestore
from datetime import datetime

router = APIRouter()
db = firestore.client()

def to_date(date_time):
    return date_time.date() if date_time else None

@router.get("/api/burndown")
async def get_burndown_data():
    now = datetime.now().date()
    sprints_ref = db.collection("sprints")
    sprints = list(sprints_ref.stream())

    active_sprint = None
    active_project_id = None

    for sprint in sprints:
        sprint_data = sprint.to_dict()
        start = sprint_data.get("start_date")
        end = sprint_data.get("end_date")
        start_date = to_date(start)
        end_date = to_date(end)

        if start_date and end_date and start_date <= now <= end_date:
            duration_days = (end_date - start_date).days + 1
            sprint_data["duration_days"] = duration_days
            active_sprint = sprint_data
            active_project_id = sprint_data.get("project_id")
            break

    if not active_sprint:
        return {"error": "No active sprint found"}

    # Obtener todos los sprints del mismo proyecto
    same_project_sprints = [
        sprint.to_dict()
        for sprint in sprints
        if sprint.to_dict().get("project_id") == active_project_id
    ]
    num_sprints = len(same_project_sprints)

    # Sumar story_points de las tareas del proyecto
    total_story_points = 0
    tasks_ref = db.collection("tasks").where("project_id", "==", active_project_id)
    tasks = tasks_ref.stream()

    for task in tasks:
        task_data = task.to_dict()
        story_points = task_data.get("story_points", 0)
        if isinstance(story_points, int):
            total_story_points += story_points

    # Calcular story_points promedio por sprint
    avg_story_points = total_story_points / num_sprints if num_sprints else 0
    active_sprint["total_story_points"] = avg_story_points

    return active_sprint