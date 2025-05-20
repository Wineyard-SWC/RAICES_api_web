from fastapi import APIRouter, HTTPException
from datetime import datetime
from firebase_admin import firestore
from datetime import datetime, timezone

router = APIRouter(tags=["Sprint Comparison"])
db = firestore.client()

def parse_firestore_date(date_value):
    if isinstance(date_value, str):
        dt = datetime.fromisoformat(date_value)
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
    - Tasks per day (burnup rate)
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
        
        for sprint in sprints:
            # Saltar sprints futuros que no son el activo
            if sprint["end_date"] > now and sprint["id"] != active_sprint["id"]:
                continue

            # Obtener tareas del sprint
            tasks = [
                t.to_dict() for t in 
                tasks_ref\
                .where("sprint_id", "==", sprint["id"])\
                .select(["story_points", "status_khanban","created_at"])\
                .stream()
            ]

        
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
            
            # Calcular tasks per day (burnup rate)
            completed_tasks = sum(1 for t in tasks if t.get("status_khanban") == "Done")
            tasks_per_day = round(completed_tasks / days_elapsed, 1)
            
            # Calcular días estimados restantes (solo para sprint activo)
            remaining_tasks = sum(1 for t in tasks if t.get("status_khanban") != "Done")
            estimated_days_remaining = round(remaining_tasks / tasks_per_day) if tasks_per_day > 0 else 0
            
            # Determinar risk assessment basado en velocidad
            risk_assessment = "Low Risk" if (completed_sp / days_elapsed) >= (total_sp / sprint["duration_weeks"] / 7) else "High Risk"

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
                "bugs_found": 0,  # TODO: Implementar conteo de bugs
                
                # Nuevos campos
                "risk_assessment": risk_assessment,
                "tasks_per_day": tasks_per_day,
                "estimated_days_remaining": estimated_days_remaining if sprint["id"] == active_sprint["id"] else None,
                "quality_metrics": {
                    "bugs_found": 0,
                    "priority_distribution": "All P2 priority"  # Esto podría calcularse si tienes los datos
                }
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