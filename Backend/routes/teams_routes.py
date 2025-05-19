from fastapi import APIRouter, HTTPException, Depends
from firebase_admin import firestore
from datetime import datetime
from typing import List, Optional
from models.team_model import TeamResponse, TeamCreate, TeamUpdate
from firebase import db, teams_ref, team_members_ref

router = APIRouter(
    tags=["teams"]
)

@router.post("/teams", response_model=TeamResponse)
async def create_team(team: TeamCreate):
    """Create a new team with members"""
    team_data = {
        "name": team.name,
        "description": team.description,
        "projectId": team.projectId,
        "createdAt": datetime.now(),
        "updatedAt": datetime.now()
    }
    
    team_ref = teams_ref.document()
    team_ref.set(team_data)
    
    for user_id in team.members:
        team_members_ref.add({
            "teamId": team_ref.id,
            "userId": user_id,
            "role": "Member",  
            "joinedAt": datetime.now()
        })
    
    members = []
    for user_id in team.members:
        user_doc = db.collection('users').document(user_id).get()
        if user_doc.exists:
            user_data = user_doc.to_dict()
            members.append({
                "id": user_id,
                "name": user_data.get("name", "Unknown"),
                "role": "Member",  # Default for now
                "tasksCompleted": 0,  # Would come from tasks data
                "currentTasks": 0,    # Would come from tasks data
                "availability": 80   # Would come from user data
            })
    
    return {
        "id": team_ref.id,
        **team_data,
        "createdAt": team_data["createdAt"].isoformat(),
        "updatedAt": team_data["updatedAt"].isoformat(),
        "members": members
    }

@router.get("/teams", response_model=List[TeamResponse])
async def get_all_teams(project_id: Optional[str] = None):
    """Get all teams or filter by project_id"""
    query = teams_ref
    
    if project_id:
        query = query.where("projectId", "==", project_id)
    
    teams = []
    for team_doc in query.stream():
        team_data = team_doc.to_dict()
        team_id = team_doc.id
        
        members = []
        member_docs = team_members_ref.where("teamId", "==", team_id).stream()
        for member_doc in member_docs:
            member_data = member_doc.to_dict()
            user_id = member_data["userId"]
            
            user_doc = db.collection('users').document(user_id).get()
            if user_doc.exists:
                user_data = user_doc.to_dict()
                
                # Get task metrics for this user (IN PROCESS)
                tasks_completed = 0
                current_tasks = 0
                
                members.append({
                    "id": user_id,
                    "name": user_data.get("name", "Unknown"),
                    "role": member_data.get("role", "Member"),
                    "tasksCompleted": tasks_completed,
                    "currentTasks": current_tasks,
                    "availability": 80  # Default for now
                })
        
        teams.append({
            "id": team_id,
            "name": team_data["name"],
            "description": team_data["description"],
            "projectId": team_data["projectId"],
            "createdAt": team_data["createdAt"].isoformat(),
            "updatedAt": team_data["updatedAt"].isoformat(),
            "members": members
        })
    
    return teams

@router.get("/teams/{team_id}", response_model=TeamResponse)
async def get_team(team_id: str):
    """Get a specific team by ID"""
    team_doc = teams_ref.document(team_id).get()
    if not team_doc.exists:
        raise HTTPException(status_code=404, detail="Team not found")
    
    team_data = team_doc.to_dict()
    
    members = []
    member_docs = team_members_ref.where("teamId", "==", team_id).stream()
    for member_doc in member_docs:
        member_data = member_doc.to_dict()
        user_id = member_data["userId"]
        
        user_doc = db.collection('users').document(user_id).get()
        if user_doc.exists:
            user_data = user_doc.to_dict()
            
            tasks_completed = 0
            current_tasks = 0
            
            members.append({
                "id": user_id,
                "name": user_data.get("name", "Unknown"),
                "role": member_data.get("role", "Member"),
                "tasksCompleted": tasks_completed,
                "currentTasks": current_tasks,
                "availability": 80
            })
    
    return {
        "id": team_id,
        "name": team_data["name"],
        "description": team_data["description"],
        "projectId": team_data["projectId"],
        "createdAt": team_data["createdAt"].isoformat(),
        "updatedAt": team_data["updatedAt"].isoformat(),
        "members": members
    }

@router.put("/teams/{team_id}", response_model=TeamResponse)
async def update_team(team_id: str, team: TeamUpdate):
    """Update a team's information"""
    team_doc = teams_ref.document(team_id).get()
    if not team_doc.exists:
        raise HTTPException(status_code=404, detail="Team not found")
    
    update_data = {
        "updatedAt": datetime.now()
    }
    
    if team.name is not None:
        update_data["name"] = team.name
    if team.description is not None:
        update_data["description"] = team.description
    
    teams_ref.document(team_id).update(update_data)
    
    if team.members is not None:
        existing_members = team_members_ref.where("teamId", "==", team_id).stream()
        for member in existing_members:
            member.reference.delete()
        
        for user_id in team.members:
            team_members_ref.add({
                "teamId": team_id,
                "userId": user_id,
                "role": "Member",  
                "joinedAt": datetime.now()
            })
    
    return await get_team(team_id)

@router.delete("/teams/{team_id}")
async def delete_team(team_id: str):
    """Delete a team and its members"""
    team_doc = teams_ref.document(team_id).get()
    if not team_doc.exists:
        raise HTTPException(status_code=404, detail="Team not found")
    
    members = team_members_ref.where("teamId", "==", team_id).stream()
    for member in members:
        member.reference.delete()
    
    teams_ref.document(team_id).delete()
    
    return {"message": "Team deleted successfully"}

@router.get("/teams/search")
async def search_teams(query: str, project_id: Optional[str] = None):
    """Search teams by name within a project (if specified)"""
    teams_query = teams_ref
    
    if project_id:
        teams_query = teams_query.where("projectId", "==", project_id)
    
    teams_query = teams_query.where("name", ">=", query).where("name", "<=", query + "\uf8ff")
    
    results = []
    for team_doc in teams_query.stream():
        team_data = team_doc.to_dict()
        results.append({
            "id": team_doc.id,
            "name": team_data["name"],
            "description": team_data["description"]
        })
    
    return results