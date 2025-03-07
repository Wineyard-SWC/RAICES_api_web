# Standard library imports

# Third-party imports
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
# Local application imports
from ia import intializeGeminiClient

router = APIRouter()
GeminiClient = intializeGeminiClient()



#PROMPTS BASE
RequirementsPrompt = "Imagina que eres un SCRUM Master con 20 años de experiencia en metodologías Agile. " \
"Tu tarea es generar requisitos funcionales y no funcionales detallados y específicos basados en " \
"la descripción del proyecto que se te proporcionará. Debes ser conciso y evitar redundancias. " \
"Responde únicamente cuando recibas una descripción clara y válida de un proyecto de software. " \
"Si la descripción del proyecto es insuficiente para generar los requerimientos, pide detalles" \
"específicos que falten. Por ejemplo, si necesitas más información sobre los usuarios finales" \
"del sistema o los objetivos específicos del proyecto, indícalo claramente. Presenta los requerimientos" \
" en una lista clara, dividiendo los funcionales y no funcionales. Para cada requerimiento," \
" proporciona una breve explicación de su propósito y cómo contribuye al éxito del proyecto."



"""
Generar requerimientos
"""

class RequestBody(BaseModel):
    project_description: str

@router.post("/generate-requirements")
async def generateRequirements(body: RequestBody):
    project_description = body.project_description
    try:
        full_prompt = RequirementsPrompt + " " + project_description
        
        response = GeminiClient.models.generate_content(
            model = "gemini-2.0-flash",
            contents={full_prompt}
        )
        return JSONResponse(content=response.text,status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
