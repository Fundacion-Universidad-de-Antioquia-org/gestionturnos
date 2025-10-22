import smtplib
from email.message import EmailMessage
import os
from dotenv import load_dotenv

load_dotenv()

def enviarCorreoGmail(destinatario, mensaje, asunto):
    # Carga las variables de entorno
    remitente_real = "noreply@fundacionudea.co" 
    password = os.getenv("PASSWORD_GMAIL_APP")

    if not all([remitente_real, password, destinatario]):
        print("Faltan datos. Revisa las variables de entorno.")
        return

    msg = EmailMessage()
    msg['Subject'] = asunto
    msg['From'] = remitente_real 
    msg['To'] = destinatario
    msg.set_content(mensaje)

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(remitente_real, password)
            smtp.send_message(msg)
        print("Correo enviado correctamente.")
    except smtplib.SMTPAuthenticationError as e:
        print("Error de autenticación:", e)
    except Exception as e:
        print("Error al enviar el correo:", e)

def enviarCorreoGmailHTML(destinatario, nombre, solicitud, fecha_registro, asunto, estado):
    remitente = "noreply@fundacionudea.co"
    password = os.getenv("PASSWORD_GMAIL_APP")

    if not all([remitente, password, destinatario]):
        print("Faltan datos. Revisa las variables de entorno.")
        return

    html = f"""
<html>
<head>
    <style>
        body {{
            background-color: #1D5031;
            font-family: Arial, sans-serif;
            color: #ffffff;
            padding: 40px;
            margin: 0;
        }}
        .content {{
            background-color: rgba(29, 80, 49, 0.2); /* verde corporativo con transparencia */
            padding: 20px;
            border-radius: 10px;
            max-width: 600px;
            margin: auto;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            text-align: left;
        }}
        .logo {{
            text-align: center;
            margin-bottom: 20px;
        }}
        h2 {{
            color: black;
        }}
        p {{
            color: black;
            line-height: 1.6;
        }}
    </style>
</head>
<body>
    <div class="content">
        <div class="logo">
            <img src="https://fundacionudea.net/web/image/website/1/logo?unique=4b2b0d3" alt="Logo Fundación UdeA" width="180">
        </div>
        <h2>Hola, {nombre}</h2>
        <p>Te queremos informar que la solicitud: <b>{solicitud}</b>, con fecha de registro: <b>{fecha_registro}</b> se encuentre en estado: <b>{estado.upper()}</b>.</p>
        <p>Se registro correctamente en nuestro sistema, el area Gestión de turnos evaluara la viabilidad de la solicitud y si es necesario se contactara contigo.</p>
        <p><b>Nota</b>¡Recuerda! Que tu solitud sera gestionanda en las fechas para las cuales fueron solicitadas.</p>
        <p><b>Gracias por usar nuestros servicios.</b></p>
        <p><b>Sistema de notificaciones - Fundación Universidad de Antioquia </b></p>
    </div>
</body>
</html>
"""

    msg = EmailMessage()
    msg['Subject'] = asunto
    msg['From'] = remitente
    msg['To'] = destinatario
    msg.set_content("Este mensaje requiere un cliente de correo compatible con HTML.")
    msg.add_alternative(html, subtype='html')

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(remitente, password)
            smtp.send_message(msg)
        print("Correo HTML enviado correctamente.")
        return True
    except smtplib.SMTPAuthenticationError as e:
        print("Error de autenticación:", e)
        return False
    except Exception as e:
        print("Error al enviar el correo:", e)
        return False
