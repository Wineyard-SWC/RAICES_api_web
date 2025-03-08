import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
import os

# Inicializar Firebase
# Obtener la ruta del archivo de credenciales
firebase_credentials_path = os.getenv("FIREBASE_CREDENTIALS_PATH")

# Verificar si la ruta al archivo es válida
if firebase_credentials_path is None:
    print("Error: la variable de entorno FIREBASE_CREDENTIALS_PATH no está definida.")
else:
    if os.path.exists(firebase_credentials_path):
        print("¡Archivo de credenciales encontrado!")
    else:
        print(f"Error: el archivo de credenciales no existe en la ruta: {firebase_credentials_path}")

cred = credentials.Certificate(firebase_credentials_path)  #
firebase_admin.initialize_app(cred)
db = firestore.client()

epics_ref = db.collection("Epics")
req_ref = db.collection("Requirements")