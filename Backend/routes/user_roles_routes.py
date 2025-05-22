from fastapi import APIRouter, HTTPException, status
from models.user_roles import UserRolesDocument, UserRolesCreate, UserRolesUpdate, UserRolesResponse, RoleDefinition
from firebase import user_roles_ref, project_users_ref
from firebase_admin import firestore
from typing import List, Optional

router = APIRouter(
    prefix="/user-roles",
    tags=["User Roles"],
    responses={404: {"description": "Not found"}},
)

# Default roles with their bitmasks
DEFAULT_ROLES = [
    {
        "idRole": "owner",
        "name": "Owner",
        "description": "Full access to all project functions",
        "bitmask": 1023,
        "is_default": True
    },
    {
        "idRole": "admin",
        "name": "Admin",
        "description": "General project administration without the ability to delete it",
        "bitmask": 510,
        "is_default": True
    },
    {
        "idRole": "developer",
        "name": "Developer",
        "description": "Doesnt have access to project management functions",
        "bitmask": 0,
        "is_default": True
    }
]

@router.post("/initialize/{user_ref}", response_model=UserRolesResponse)
async def initialize_default_roles(user_ref: str):
    """
    Initialize the default user roles in the database for a specific user.
    Creates a single document with a list of all default roles.
    """
    # Check if user already has roles document
    query = user_roles_ref.where("userRef", "==", user_ref).limit(1).get()
    
    if query:
        # User already has roles
        role_doc = query[0]
        role_data = role_doc.to_dict()
        role_data["id"] = role_doc.id
        return UserRolesResponse(**role_data)
    
    # Create new roles document with server timestamps
    roles_list = [RoleDefinition(**role) for role in DEFAULT_ROLES]
    
    user_roles_doc = {
        "userRef": user_ref,
        "roles": [role.dict() for role in roles_list],
        "createdAt": firestore.SERVER_TIMESTAMP,
        "updatedAt": firestore.SERVER_TIMESTAMP
    }
    
    doc_ref = user_roles_ref.document()
    user_roles_doc["id"] = doc_ref.id
    doc_ref.set(user_roles_doc)
    
    # Get the document after creation to get the proper timestamps
    created_doc = doc_ref.get().to_dict()
    created_doc["id"] = doc_ref.id
    
    return UserRolesResponse(**created_doc)

@router.get("/{user_ref}", response_model=UserRolesResponse)
async def get_user_roles(user_ref: str):
    """Get all roles for a specific user."""
    query = user_roles_ref.where("userRef", "==", user_ref).limit(1).get()
    
    if not query:
        raise HTTPException(
            status_code=404,
            detail=f"No roles found for user '{user_ref}'"
        )
    
    role_doc = query[0]
    role_data = role_doc.to_dict()
    role_data["id"] = role_doc.id
    
    return UserRolesResponse(**role_data)

@router.patch("/{document_id}", response_model=UserRolesResponse)
async def update_user_roles(document_id: str, roles_update: UserRolesUpdate):
    """Update roles for a user."""
    role_doc = user_roles_ref.document(document_id).get()
    
    if not role_doc.exists:
        raise HTTPException(
            status_code=404,
            detail=f"User roles document with ID '{document_id}' not found"
        )
    
    update_data = {}
    
    if roles_update.roles is not None:
        update_data["roles"] = [role.dict() for role in roles_update.roles]
    
    # Use Firebase server timestamp
    update_data["updatedAt"] = firestore.SERVER_TIMESTAMP
    
    user_roles_ref.document(document_id).update(update_data)
    
    # Get the updated document
    updated_doc = user_roles_ref.document(document_id).get()
    updated_data = updated_doc.to_dict()
    updated_data["id"] = updated_doc.id
    
    return UserRolesResponse(**updated_data)

@router.get("/bitmask/{role_id_or_name}", response_model=int)
async def get_role_bitmask(role_id_or_name: str):
    """
    Get the bitmask value for a specific role by ID or name.
    Works with both idRole values and display names.
    """
    for role in DEFAULT_ROLES:
        if role["idRole"] == role_id_or_name or role["name"] == role_id_or_name:
            return role["bitmask"]
    
    query = user_roles_ref.get()
    
    for doc in query:
        roles_list = doc.to_dict().get("roles", [])
        for role in roles_list:
            # Check both idRole and name fields
            if (role.get("idRole") == role_id_or_name or 
                role.get("name") == role_id_or_name):
                return role.get("bitmask", 0)
    
    raise HTTPException(
        status_code=404,
        detail=f"Role with ID or name '{role_id_or_name}' not found"
    )
