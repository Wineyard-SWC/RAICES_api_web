# Standard library imports

# Third-party imports
from fastapi import APIRouter
# Local application imports

router = APIRouter()

@router.get("/")
def read_root():
    return {"Hello": "Welcome to RAICES API"}