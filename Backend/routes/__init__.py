# Standard library imports

# Third-party imports

# Local application imports
from .app_routes import router as app_router       # <--- Cambiar name por el nombre de la ruta.py

from .users_routes import router as user_router 
from .projects_routes import router as project_router 
from .project_users_routes import router as project_user_router 
from .req_routes import router as requirements_router
from .epic_routes import router as epic_router 
from .userStorie_routes import router as userStorie_router
from .users_search_routes import router as users_search_router
from .tasks_routes import router as tasks_router
from .sprint_routes import router as sprints_router
from .burndown_routes import router as burndown_router 
from .velocity_routes import router as velocity_router
from .permissions_routes import router as permissions_router


#from .email_routes import router as emai_router

