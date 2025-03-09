# Standard library imports
import asyncio 
import os
# Third-party imports
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
# Local application imports
from ia import ProjectAssistantAI as Assistant


router = APIRouter()

RequirementsGenerativeAI = Assistant(subdirectory='requirements_pdfs')

#PROMPTS BASE
FunctionalRequirementsPrompt = "Imagina que eres un SCRUM Master con 20 años de experiencia en metodologías Agile. " \
"Tu tarea es generar requisitos funcionales detallados y específicos basados en " \
"la descripción del proyecto que se te proporcionará. Debes ser conciso y evitar redundancias. " \
"Responde únicamente cuando recibas una descripción clara y válida de un proyecto de software. " \
"Si la descripción del proyecto es insuficiente para generar los requerimientos, pide detalles" \
"específicos que falten. Por ejemplo, si necesitas más información sobre los usuarios finales" \
"del sistema o los objetivos específicos del proyecto, indícalo claramente. Presenta los requerimientos" \
" en una lista clara. Basate en el siguiente ejemplo: " \
"1. Inicio de sesión de usuario: El sistema debe permitir a los usuarios iniciar sesión utilizando un nombre de usuario y contraseña válidos."\
"2. Procesamiento de Negocios: El sistema debe procesar los pagos con tarjeta de crédito y proporcionar a los usuarios un recibo cuando las transacciones sean exitosas."

NonFunctionalRequirementsPrompt = "Imagina que eres un SCRUM Master con 20 años de experiencia en metodologías Agile. " \
"Tu tarea es generar requisitos no funcionales detallados y específicos basados en " \
"la descripción del proyecto que se te proporcionará. Debes ser conciso y evitar redundancias. " \
"Responde únicamente cuando recibas una descripción clara y válida de un proyecto de software. " \
"Si la descripción del proyecto es insuficiente para generar los requerimientos, pide detalles" \
"específicos que falten. Por ejemplo, si necesitas más información sobre los usuarios finales" \
"del sistema o los objetivos específicos del proyecto, indícalo claramente. Presenta los requerimientos" \
" en una lista clara. Basate en el siguiente ejemplo: " \
"Velocidad de rendimiento:El sistema debe procesar las solicitudes de los usuarios en un plazo promedio de 2 segundos, incluso con mucho tráfico de usuarios."\
"Disponibilidad del sistema:El sistema debe mantener un tiempo de actividad del 99.9 % para garantizar que los usuarios tengan acceso constante."


class RequestBody(BaseModel):
    project_description: str

#Generar requerimientos funcionales
def generate_functional_requirements(project_description):

    return RequirementsGenerativeAI.generate_content(
        query=project_description,
        preprompt=FunctionalRequirementsPrompt
    )
    
#Generar requerimientos no funcionales
def generate_non_functional_requirements(project_description):
    return  RequirementsGenerativeAI.generate_content(
        query=project_description,
        preprompt=NonFunctionalRequirementsPrompt
    )
    

"""
Generar requerimientos funcionales 
"""
@router.post("/generate-requirements")
async def generate_requirements(body: RequestBody):
    project_description = body.project_description
    try:
        functional_response = await generate_functional_requirements(project_description),
        non_functional_response = await generate_non_functional_requirements(project_description)
        return JSONResponse(content={
            "FR": functional_response,
            "NFR": non_functional_response
        }, status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))