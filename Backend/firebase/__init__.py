# firebase_config.py
from dotenv import load_dotenv
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore, auth

load_dotenv()

# Obtener las credenciales de Firebase desde el entorno
firebase_credentials = os.getenv("FIREBASE_CREDENTIALS")

if firebase_credentials:
    cred_dict = json.loads(firebase_credentials)  # Convertir el JSON en un diccionario
    cred = credentials.Certificate(cred_dict)
    
    # Verificar si ya está inicializado, si no, inicializar solo una vez
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
else:
    raise ValueError("No se encontraron credenciales de Firebase en las variables de entorno")


db = firestore.client()

epics_ref = db.collection("Epics")
req_ref = db.collection("Requirements")

users_ref = db.collection("users")
projects_ref = db.collection("projects")
project_users_ref = db.collection("project_users")
