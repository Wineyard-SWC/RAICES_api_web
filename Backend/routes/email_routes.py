import os
import smtplib
from email.mime.text import MIMEText

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel

from firebase_admin import auth
from typing import Optional

# Importa users_ref (o el que uses) si necesitas validar algo adicional
# from firebase import users_ref

router = APIRouter()

# ------------------------------------------------------------------------------
# MODEL (Request body)
# ------------------------------------------------------------------------------
class EmailInvitationData(BaseModel):
    recipientEmail: str
    invitationLink: str
    projectTitle: str

@router.post("/email")
def send_invitation_email(
    email_data: EmailInvitationData,
    current_user: dict = Depends(verify_token)
):
    """
    Envía un correo de invitación a un usuario, 
    usando los datos proporcionados en la petición POST.

    Requiere que en el header se incluya un 'Authorization: Bearer <token>' válido.
    """

    # --------------------------------------------------------------------------
    # EJEMPLO DE USUARIO AUTORIZADO
    # (Opcional) Verifica algún campo adicional, 
    # por ejemplo si el current_user tiene rol "admin" o similar
    # --------------------------------------------------------------------------
    # user_role = current_user.get("role", "user")
    # if user_role != "admin":
    #     raise HTTPException(status_code=403, detail="Not enough privileges")

    # --------------------------------------------------------------------------
    # CONFIGURACIÓN SMTP (EJEMPLO CON GMAIL)
    # --------------------------------------------------------------------------
    SMTP_USERNAME = os.environ.get("SMTP_USERNAME")  # tu correo o usuario
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")  # tu contraseña o app-password
    SMTP_HOST = "smtp.gmail.com"
    SMTP_PORT = 587

    if not SMTP_USERNAME or not SMTP_PASSWORD:
        raise HTTPException(
            status_code=500,
            detail="SMTP credentials not set in environment variables"
        )

    # --------------------------------------------------------------------------
    # CONSTRUIMOS EL CONTENIDO DEL EMAIL
    # --------------------------------------------------------------------------
    subject = f"Invitación al proyecto: {email_data.projectTitle}"
    body = (
        f"Hola,\n\n"
        f"Has sido invitado a unirte al proyecto '{email_data.projectTitle}'.\n"
        f"Para unirte, haz clic en el siguiente enlace:\n"
        f"{email_data.invitationLink}\n\n"
        f"¡Esperamos que puedas unirte pronto!"
    )

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = SMTP_USERNAME  # Remitente (tu correo)
    msg["To"] = email_data.recipientEmail

    # --------------------------------------------------------------------------
    # ENVÍO DEL CORREO
    # --------------------------------------------------------------------------
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()  # Establece conexión segura
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(
                from_addr=SMTP_USERNAME,
                to_addrs=[email_data.recipientEmail],
                msg=msg.as_string()
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error sending email: {str(e)}"
        )

    return {"success": True, "message": f"Email sent to {email_data.recipientEmail}"}
'''