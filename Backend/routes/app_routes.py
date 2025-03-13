import firebase_admin
from firebase_admin import auth
from firebase import users_ref
from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Optional

router = APIRouter()

@router.get("/")
def read_root():
    return {"Hello": "Welcome to RAICES API"}

def verify_token(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing token")
    
    token_parts = authorization.split()
    if len(token_parts) != 2 or token_parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid token format")
    
    token = token_parts[1]
    
    try:
        print(f"Verificando token: {token}")
        decoded_token = auth.verify_id_token(token, check_revoked=True, clock_skew_seconds=60)
        print(f"Token verificado: {decoded_token}")

        uid = decoded_token.get("uid")
        name = decoded_token.get("name")
        email = decoded_token.get("email")
        picture = decoded_token.get("picture")

        # Verificar si el usuario ya existe en Firestore
        user_doc = users_ref.document(uid).get()
        if not user_doc.exists:
            # Si no existe, lo creamos con rol "user" por defecto
            users_ref.document(uid).set({
                "name": name,
                "email": email,
                "role": "user",  # Rol por defecto
                "picture": picture
            })

        return decoded_token
    except Exception as e:
        print(f"Error verificando el token: {e}")
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

@router.get("/token")
async def get_profile(current_user: dict = Depends(verify_token)):
    return {"message": "User authenticated", "user": current_user}
