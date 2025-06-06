from fastapi import APIRouter, HTTPException
from datetime import datetime
from firebase_admin import firestore
from datetime import datetime, timezone, timedelta
from models.task_model import GraphicsRequest

router = APIRouter(tags=["Sprint Details"])
db = firestore.client()

def to_date(date_time):
    return date_time.date() if date_time else None

def get_value(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)

def parse_firestore_date(date_value):
    if isinstance(date_value, str):
        try:
            date_value = date_value.replace("Z", "+00:00")
            dt = datetime.fromisoformat(date_value)
        except Exception:
            return None
    elif isinstance(date_value, datetime):
        dt = date_value
    elif hasattr(date_value, "timestamp"):
        dt = datetime.fromtimestamp(date_value.timestamp())
    elif hasattr(date_value, "seconds") and hasattr(date_value, "nanos"):
        dt = datetime.fromtimestamp(date_value.seconds + date_value.nanos / 1e9)
    else:
        return None

    # Asegurar que el datetime tenga zona horaria UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt


@router.get("/api/sprints/comparison", response_model=list)
async def get_sprint_comparison(projectId: str):
    """
    Obtiene la comparación de sprints para un proyecto, incluyendo:
    - Sprint actual (basado en fechas)
    - Sprints anteriores completados
    - Métricas de velocidad, completado, cambios de scope
    - Risk assessment
    - Quality metrics
    """
    try:
        now = datetime.now(timezone.utc)
        
        # 1. Obtener todos los sprints del proyecto
        sprints_ref = db.collection("sprints").where("project_id", "==", projectId)
        sprints = []
        
        for doc in sprints_ref.stream():
            sprint = doc.to_dict()
            sprint["id"] = doc.id
            
            # Parsear fechas
            sprint["start_date"] = parse_firestore_date(sprint.get("start_date"))
            sprint["end_date"] = parse_firestore_date(sprint.get("end_date"))
            
            if not sprint["start_date"] or not sprint["end_date"]:
                continue
                
            sprints.append(sprint)

        if not sprints:
            return []
        # 2. Identificar sprint activo (rango de fechas actual)
        active_sprint = next(
            (s for s in sprints if s["start_date"] <= now <= s["end_date"]),
            None
        )

        # 3. Si no hay activo, usar el más reciente por fecha de inicio
        if not active_sprint:
            active_sprint = max(sprints, key=lambda x: x["start_date"])

        # 4. Procesar cada sprint para la comparación
        comparison_data = []
        tasks_ref = db.collection("tasks")
        bugs_ref = db.collection("bugs")
        
        for sprint in sprints:
            # Saltar sprints futuros que no son el activo
            if sprint["end_date"] > now and sprint["id"] != active_sprint["id"]:
                continue

            # Obtener tareas del sprint
            tasks = [
                t.to_dict() for t in 
                tasks_ref\
                .where("sprint_id", "==", sprint["id"])\
                .select(["story_points", "status_khanban", "created_at"])\
                .stream()
            ]

            # Obtener bugs del sprint
            bugs = [
                b.to_dict() for b in 
                bugs_ref\
                .where("sprintId", "==", sprint["id"])\
                .select(["severity"])\
                .stream()
            ]
            total_bugs = len(bugs)

            # Calcular métricas básicas
            total_sp = sum(t.get("story_points", 0) for t in tasks)
            completed_sp = sum(
                t.get("story_points", 0) for t in tasks 
                if t.get("status_khanban") == "Done"
            )
            
            scope_changes = sum(
                1 for t in tasks 
                if parse_firestore_date(t.get("created_at")) > sprint["start_date"]
            )

            # Calcular días transcurridos en el sprint
            days_elapsed = (now - sprint["start_date"]).days if sprint["id"] == active_sprint["id"] else (sprint["end_date"] - sprint["start_date"]).days
            days_elapsed = max(1, days_elapsed)  # Evitar división por cero

            days_left = (sprint["end_date"] - now).days if sprint["id"] == active_sprint["id"] else 0
            days_left = max(0, days_left)  # No permitir días negativos

            # Determinar risk assessment basado en múltiples factores
            velocity = completed_sp / days_elapsed
            average_velocity = total_sp / (sprint["duration_weeks"] * 7)
            risk_assessment = "Low Risk"

            if velocity < average_velocity * 0.8 or scope_changes > 5 or total_bugs > 10:
                risk_assessment = "Medium Risk"
            if velocity < average_velocity * 0.5 or scope_changes > 10 or total_bugs > 20:
                risk_assessment = "High Risk"

            sprint_data = {
                "sprint_id": sprint["id"],
                "sprint_name": sprint.get("name", f"Sprint {sprint['id'][:6]}"),
                "is_current": sprint["id"] == active_sprint["id"],
                "total_story_points": total_sp,
                "completed_story_points": completed_sp,
                "completion_percentage": round(
                    (completed_sp / total_sp * 100) if total_sp > 0 else 0
                ),
                "scope_changes": scope_changes,
                "bugs_found": total_bugs,
                "risk_assessment": risk_assessment,
                "velocity": velocity,
                "average_velocity": average_velocity,
                "days_left": days_left,
                "start_date": sprint["start_date"].isoformat(),
                "end_date": sprint["end_date"].isoformat()
            }

            comparison_data.append(sprint_data)

        # Ordenar: current primero, luego por fecha descendente
        comparison_data.sort(
            key=lambda x: (not x["is_current"], x["sprint_id"]), 
            reverse=True
        )

        return comparison_data or []

    except Exception as e:
        raise HTTPException(500, f"Failed to generate sprint comparison: {str(e)}")
    

@router.post("/api/burndown")
async def get_burndown_data(payload: GraphicsRequest):
    project_id = payload.projectId
    tasks = payload.tasks or []

    now = datetime.now(timezone.utc).date()

    # Obtener el sprint activo
    sprints_ref = db.collection("sprints").where("project_id", "==", project_id)
    active_sprint = None
    
    for doc in sprints_ref.stream():
        sprint = doc.to_dict()
        sprint["id"] = doc.id
        start_date = parse_firestore_date(sprint.get("start_date"))
        end_date = parse_firestore_date(sprint.get("end_date"))
        
        if start_date and end_date:
            sprint["start_date"] = start_date.date()
            sprint["end_date"] = end_date.date()
            if sprint["start_date"] <= now <= sprint["end_date"]:
                active_sprint = sprint
                break

    if not active_sprint:
        return {"error": "No active sprint found for this project"}

    # Obtener todas las tareas del sprint
    if not tasks:
        tasks_query = db.collection("tasks").where("sprint_id", "==", active_sprint["id"])
        tasks = [t.to_dict() for t in tasks_query.stream()]

    # Procesar datos para el burndown
    total_sp = sum(get_value(t, "story_points", 0) for t in tasks)

    sprint_days = (active_sprint["end_date"] - active_sprint["start_date"]).days + 1
    
    # Calcular progreso diario
    daily_progress = []
    current_date = active_sprint["start_date"]
    
    # Obtener fechas de completado de tareas
    task_completion_dates = []
    for task in tasks:
        if get_value(task, "status_khanban", "").lower() == "done":
            completed_at = parse_firestore_date(
                get_value(task, "date_completed") or get_value(task, "date_modified")
            )
            if completed_at:
                task_completion_dates.append({
                    "date": completed_at.date(),
                    "sp": get_value(task, "story_points", 0)
                })

    # Calcular SP completados por día
    sp_completed_per_day = {}
    for day in range(sprint_days):
        current_date = active_sprint["start_date"] + timedelta(days=day)
        sp_completed = sum(
            t["sp"] for t in task_completion_dates 
            if t["date"] == current_date
        )
        sp_completed_per_day[current_date] = sp_completed

    # Generar datos para el chart
    chart_data = []
    cumulative_completed = 0
    ideal_drop_per_day = total_sp / (sprint_days - 1) if sprint_days > 1 else total_sp
    
    for day in range(sprint_days):
        current_date = active_sprint["start_date"] + timedelta(days=day)
        day_label = f"Day {day+1}"
        
        # Calcular completado acumulado
        daily_completed = sp_completed_per_day.get(current_date, 0)
        cumulative_completed += daily_completed
        
        remaining = max(total_sp - cumulative_completed, 0)
        ideal = max(total_sp - (ideal_drop_per_day * day), 0)
        
        chart_data.append({
            "day": day_label,
            "date": current_date.isoformat(),
            "Remaining": remaining,
            "Ideal": round(ideal, 2),
            "Completed": daily_completed,
            "CompletedCumulative": cumulative_completed
        })

    return {
        "sprint_info": {
            "name": active_sprint.get("name", f"Sprint {active_sprint['id'][:6]}"),
            "start_date": active_sprint["start_date"].isoformat(),
            "end_date": active_sprint["end_date"].isoformat(),
            "total_story_points": total_sp,
            "duration_days": sprint_days
        },
        "chart_data": chart_data
    }


@router.post("/api/velocitytrend")
async def get_velocity_trend(payload: GraphicsRequest):
    projectId = payload.projectId
    tasks_from_payload = payload.tasks or []

    now = datetime.now(timezone.utc)
    
    # 1. Obtener todos los sprints del proyecto y parsear fechas
    sprints_snapshots = db.collection("sprints").where("project_id", "==", projectId).stream()
    sprints_data = []
    
    for snap in sprints_snapshots:
        data = snap.to_dict()
        data["id"] = snap.id
        
        # Parsear fechas
        data["start_date"] = parse_firestore_date(data.get("start_date"))
        data["end_date"] = parse_firestore_date(data.get("end_date"))
        
        if not data["start_date"] or not data["end_date"]:
            continue
            
        sprints_data.append(data)

    if not sprints_data:
        return {"error": "No sprints found for this project"}

    # 2. Filtrar sprints: solo pasados y el actual (excluir futuros)
    filtered_sprints = []
    for sprint in sprints_data:
        # Incluir sprint si ya terminó o está en progreso
        if sprint["end_date"] <= now or (sprint["start_date"] <= now <= sprint["end_date"]):
            filtered_sprints.append(sprint)

    # 3. Ordenar sprints por fecha de inicio
    filtered_sprints.sort(key=lambda x: x["start_date"])

    # 4. Preparar estructura para velocity
    velocity = {
        sprint["id"]: {
            "Planned": 0,
            "Actual": 0,
            "sprint": sprint.get("name") or f"Sprint {sprint.get('number', sprint['id'][:6])}",
            "start_date": sprint["start_date"].isoformat(),
            "end_date": sprint["end_date"].isoformat()
        }
        for sprint in filtered_sprints
    }

    # 5. Procesar tareas
    if tasks_from_payload:
        # Procesar las tareas recibidas desde el frontend
        for task in tasks_from_payload:
            sprint_id = task.sprint_id
            if sprint_id in velocity:
                sp = task.story_points or 0
                velocity[sprint_id]["Planned"] += sp
                if task.status_khanban and task.status_khanban.strip().lower() == "done":
                    velocity[sprint_id]["Actual"] += sp
    else:
        # Obtener tareas desde Firestore si no se proporcionaron
        tasks_snapshots = db.collection("tasks").where("project_id", "==", projectId).stream()
        for snap in tasks_snapshots:
            data = snap.to_dict()
            sprint_id = data.get("sprint_id")
            if sprint_id in velocity:
                sp = data.get("story_points", 0)
                if isinstance(sp, int):
                    velocity[sprint_id]["Planned"] += sp
                    if data.get("status_khanban", "").strip().lower() == "done":
                        velocity[sprint_id]["Actual"] += sp

    # Convertir a lista ordenada por fecha
    velocity_list = list(velocity.values())
    velocity_list.sort(key=lambda x: x["start_date"])

    return velocity_list