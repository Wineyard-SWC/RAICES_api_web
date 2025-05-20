from fastapi import APIRouter, HTTPException
from firebase_admin import firestore
from datetime import datetime
from typing import List
from models.team_model import TeamResponse, TeamCreate, TeamUpdate, TeamMetricsResponse
from firebase import db, teams_ref
from datetime import datetime, timezone

router = APIRouter(
    tags=["teams"]
)

async def _calculate_user_metrics(user_id: str, project_id: str) -> dict:
    # Obtener todas las tareas del proyecto
    tasks_query = (
        db.collection('tasks')
        .where('project_id', '==', project_id)
        .stream()
    )
    
    current_tasks = 0
    completed_tasks = 0
    
    for task in tasks_query:
        task_data = task.to_dict()
        assignees = task_data.get('assignee', [])
        
        # Verificar si el usuario está en los asignados
        if any(assignee.get('id') == user_id for assignee in assignees):
            if task_data.get('status_khanban') == 'Done':
                completed_tasks += 1
            else:
                current_tasks += 1
    
    # Calcular disponibilidad (80% base - 5% por cada tarea actual, mínimo 20%)
    availability = max(20, 80 - (current_tasks * 5))
    
    return {
        'tasksCompleted': completed_tasks,
        'currentTasks': current_tasks,
        'availability': availability
    }

async def _get_user_details(user_id: str, project_id: str) -> dict:
    user_doc = db.collection('users').document(user_id).get()
    if not user_doc.exists:
        return None

    user_data = user_doc.to_dict()
    
    # Calcular métricas basadas en tareas
    metrics = await _calculate_user_metrics(user_id, project_id)
    
    return {
        "id": user_id,
        "name": user_data.get("name", "Unknown"),
        "role": "Member",
        "tasksCompleted": metrics['tasksCompleted'],
        "currentTasks": metrics['currentTasks'],
        "availability": metrics['availability']
    }

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

# Crear equipo
@router.post("/projects/{project_id}/teams", response_model=TeamResponse)
async def create_team(project_id: str, team: TeamCreate):
    """Create a new team under a project"""
    members = []
    for user_id in team.members:
        user_details = await _get_user_details(user_id, project_id)
        if user_details:
            members.append(user_details)

    if not members:
        raise HTTPException(status_code=400, detail="No valid members provided")

    now = datetime.now()
    team_data = {
        "name": team.name,
        "description": team.description,
        "projectId": project_id,
        "members": members,
        "createdAt": now,
        "updatedAt": now
    }

    team_ref = teams_ref.document()
    team_ref.set(team_data)

    return {
        "id": team_ref.id,
        **team_data,
        "createdAt": now.isoformat(),
        "updatedAt": now.isoformat()
    }

# Obtener todos los equipos de un proyecto
@router.get("/projects/{project_id}/teams", response_model=List[TeamResponse])
async def get_all_teams(project_id: str):
    """Get all teams in a specific project with calculated metrics"""
    query = teams_ref.where("projectId", "==", project_id)
    teams = []

    for team_doc in query.stream():
        team_data = team_doc.to_dict()
        
        # Actualizar métricas para cada miembro
        updated_members = []
        for member in team_data.get("members", []):
            metrics = await _calculate_user_metrics(member["id"], project_id)
            updated_member = {
                **member,
                "tasksCompleted": metrics['tasksCompleted'],
                "currentTasks": metrics['currentTasks'],
                "availability": metrics['availability']
            }
            updated_members.append(updated_member)
        
        team_data["members"] = updated_members
        teams.append({
            "id": team_doc.id,
            **team_data,
            "createdAt": team_data["createdAt"].isoformat(),
            "updatedAt": team_data["updatedAt"].isoformat()
        })

    return teams

# Obtener equipo por ID y proyecto
@router.get("/projects/{project_id}/teams/{team_id}", response_model=TeamResponse)
async def get_team(project_id: str, team_id: str):
    """Get a specific team by ID within a project"""
    team_doc = teams_ref.document(team_id).get()
    if not team_doc.exists:
        raise HTTPException(status_code=404, detail="Team not found")

    team_data = team_doc.to_dict()
    if team_data.get("projectId") != project_id:
        raise HTTPException(status_code=400, detail="Team does not belong to this project")

    updated_members = []
    for member in team_data.get("members", []):
        metrics = await _calculate_user_metrics(member["id"], project_id)
        updated_member = {
            **member,
            "tasksCompleted": metrics['tasksCompleted'],
            "currentTasks": metrics['currentTasks'],
            "availability": metrics['availability']
        }
        updated_members.append(updated_member)
    
    team_data["members"] = updated_members

    return {
        "id": team_id,
        **team_data,
        "createdAt": team_data["createdAt"].isoformat(),
        "updatedAt": team_data["updatedAt"].isoformat()
    }

# Actualizar equipo
@router.put("/projects/{project_id}/teams/{team_id}", response_model=TeamResponse)
async def update_team(project_id: str, team_id: str, team: TeamUpdate):
    """Update a team's information"""
    team_ref = teams_ref.document(team_id)
    team_doc = team_ref.get()
    if not team_doc.exists:
        raise HTTPException(status_code=404, detail="Team not found")

    team_data = team_doc.to_dict()
    if team_data.get("projectId") != project_id:
        raise HTTPException(status_code=400, detail="Team does not belong to this project")

    update_data = {
        "updatedAt": datetime.now()
    }

    if team.name is not None:
        update_data["name"] = team.name
    if team.description is not None:
        update_data["description"] = team.description

    if team.members is not None:
        members = []
        for user_id in team.members:
            user_details = await _get_user_details(user_id, project_id)
            if user_details:
                members.append(user_details)
        if members:
            update_data["members"] = members

    team_ref.update(update_data)

    return await get_team(project_id, team_id)

# Eliminar equipo
@router.delete("/projects/{project_id}/teams/{team_id}")
async def delete_team(project_id: str, team_id: str):
    """Delete a team"""
    team_ref = teams_ref.document(team_id)
    team_doc = team_ref.get()
    if not team_doc.exists:
        raise HTTPException(status_code=404, detail="Team not found")

    team_data = team_doc.to_dict()
    if team_data.get("projectId") != project_id:
        raise HTTPException(status_code=400, detail="Team does not belong to this project")

    team_ref.delete()
    return {"message": "Team deleted successfully"}

# Buscar equipos por nombre dentro de un proyecto
@router.get("/projects/{project_id}/teams/search")
async def search_teams(project_id: str, query: str):
    """Search teams by name within a project"""
    teams_query = (
        teams_ref
        .where("projectId", "==", project_id)
        .where("name", ">=", query)
        .where("name", "<=", query + "\uf8ff")
    )

    results = []
    for team_doc in teams_query.stream():
        team_data = team_doc.to_dict()
        results.append({
            "id": team_doc.id,
            "name": team_data["name"],
            "description": team_data["description"]
        })

    return results

@router.get("/projects/{project_id}/teams/{team_id}/metrics", response_model=TeamMetricsResponse)
async def get_team_metrics(project_id: str, team_id: str):
    """Get metrics for a specific team based on active sprint"""
    # 1. Verificar que el equipo exista
    team_doc = teams_ref.document(team_id).get()
    if not team_doc.exists:
        raise HTTPException(status_code=404, detail="Team not found")
    
    team_data = team_doc.to_dict()
    if team_data.get("projectId") != project_id:
        raise HTTPException(status_code=400, detail="Team does not belong to this project")

    # 2. Obtener sprint activo usando la misma lógica que sprint comparison
    now = datetime.now(timezone.utc)
    sprints_ref = db.collection("sprints").where("project_id", "==", project_id)
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
        raise HTTPException(status_code=404, detail="No sprints found for this project")

    # Identificar sprint activo (rango de fechas actual)
    active_sprint = next(
        (s for s in sprints if s["start_date"] <= now <= s["end_date"]),
        None
    )

    # Si no hay activo, usar el más reciente por fecha de inicio
    if not active_sprint:
        active_sprint = max(sprints, key=lambda x: x["start_date"])

    # 3. Obtener todas las tareas del sprint activo asignadas a miembros del equipo
    team_member_ids = [member['id'] for member in team_data.get('members', [])]
    
    tasks_query = (
        db.collection('tasks')
        .where('project_id', '==', project_id)
        .where('sprint_id', '==', active_sprint['id'])
        .stream()
    )
    
    # 4. Calcular métricas
    total_tasks = 0
    completed_tasks = 0
    in_progress_tasks = 0
    total_story_points = 0
    completed_story_points = 0
    
    for task in tasks_query:
        task_data = task.to_dict()
        assignees = task_data.get('assignee', [])
        
        # Verificar si algún miembro del equipo está asignado a esta tarea
        if any(assignee.get('id') in team_member_ids for assignee in assignees):
            total_tasks += 1
            total_story_points += task_data.get('story_points', 0)
            
            if task_data.get('status_khanban') == 'Done':
                completed_tasks += 1
                completed_story_points += task_data.get('story_points', 0)
            elif task_data.get('status_khanban') in ['In Progress', 'In Review']:
                in_progress_tasks += 1

    # 5. Calcular métricas derivadas
    sprint_duration = (active_sprint['end_date'] - active_sprint['start_date']).days
    days_elapsed = (now - active_sprint['start_date']).days
    
    # Velocidad (story points completados por día)
    velocity = completed_story_points / days_elapsed if days_elapsed > 0 else 0
    
    # Porcentaje de tareas completadas
    tasks_completed_pct = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
    
    # Porcentaje de tareas en progreso
    tasks_in_progress_pct = (in_progress_tasks / total_tasks * 100) if total_tasks > 0 else 0
    
    # Tiempo promedio por historia (días por story point)
    avg_story_time = days_elapsed / completed_story_points if completed_story_points > 0 else 0
    
    # Progreso del sprint
    sprint_progress = (days_elapsed / sprint_duration * 100) if sprint_duration > 0 else 0

    return TeamMetricsResponse(
        velocity=round(velocity, 2),
        mood=75,  # Hardcodeado por ahora
        tasks_completed=round(tasks_completed_pct),
        tasks_in_progress=round(tasks_in_progress_pct),
        avg_story_time=round(avg_story_time, 1),
        sprint_progress=round(sprint_progress, 1)
    )