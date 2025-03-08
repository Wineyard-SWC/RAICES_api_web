import os
import json
import firebase_admin
from firebase_admin import credentials, firestore

# Inicializar Firebase
# Obtener la ruta del archivo de credenciales
firebase_credentials = os.getenv("FIREBASE_CREDENTIALS")

if firebase_credentials:
    cred_dict = json.loads(firebase_credentials)  # Convertir el JSON en un diccionario
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)
else:
    raise ValueError("No se encontraron credenciales de Firebase en las variables de entorno")

db = firestore.client()

epics_ref = db.collection("Epics")
req_ref = db.collection("Requirements")