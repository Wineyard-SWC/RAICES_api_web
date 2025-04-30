# firebase_config.py
#from dotenv import load_dotenv
import os
import firebase_admin
from firebase_admin import credentials, firestore, auth

from dotenv import load_dotenv
print("load_dotenv imported correctly")

load_dotenv()
# Obtener las credenciales de Firebase desde el entorno
cred_dict= {
    "type": os.getenv("TYPE"),
    "project_id": os.getenv("PROJECT_ID"),
    "private_key_id": os.getenv("PRIVATE_KEY_ID"),
    "private_key": os.getenv("PRIVATE_KEY").replace("\\n", "\n"),  
    "client_email": os.getenv("CLIENT_EMAIL"),
    "client_id": os.getenv("CLIENT_ID"),
    "auth_uri": os.getenv("AUTH_URI"),
    "token_uri": os.getenv("TOKEN_URI"),
    "auth_provider_x509_cert_url": os.getenv("AUTH_PROVIDER_CERT_URL"),
    "client_x509_cert_url": os.getenv("CLIENT_CERT_URL")
}


if cred_dict:
    
    cred = credentials.Certificate(cred_dict)
    
    # Verificar si ya está inicializado, si no, inicializar solo una vez
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
else:
    raise ValueError("No se encontraron credenciales de Firebase en las variables de entorno")


db = firestore.client()

users_ref = db.collection("users")
projects_ref = db.collection("projects")
project_users_ref = db.collection("project_users")
req_ref = db.collection("requirements")
epics_ref = db.collection("epics")
userstories_ref = db.collection("userStories")
tasks_ref = db.collection("tasks")
sprints_ref      = db.collection("sprints")
