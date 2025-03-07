"""
Archivo: main.py
Descripción: Este módulo inicia la aplicación FastAPI, incluyendo la configuración del servidor.
Autores: Abdiel Fritsche Barajas, Oscar Zhao Xu
Fecha de Creación: 05-03-2025
"""

# Standard library imports
# Third-party imports
# Local application imports
from app import create_app


if __name__ == "__main__":
    import uvicorn
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)