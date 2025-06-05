from fastapi import APIRouter, HTTPException
from firebase import db

router = APIRouter(tags=["Store"])
office_state_ref = db.collection("office_state")

@router.put("/user/{user_id}/store_state")
def save_store_state(user_id: str, payload: dict):
    office_state_ref.document(user_id).set(payload)
    return {"message": "Store state saved successfully"}

@router.get("/user/{user_id}/store_state")
def get_store_state(user_id: str):
    doc = office_state_ref.document(user_id).get()
    if not doc.exists:
        return {"used_sp": 0, "items": {}}
    return doc.to_dict()