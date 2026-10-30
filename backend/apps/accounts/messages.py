"""Textos de los correos de cuentas, por idioma (M8 los pasará a las plantillas)."""

PASSWORD_RESET = {
    "es": {
        "subject": "Recupera tu contraseña",
        "body": (
            "Hola {name},\n\nPara crear una contraseña nueva abre este enlace:\n{link}\n\n"
            "Si no lo pediste, ignora este correo."
        ),
    },
    "en": {
        "subject": "Reset your password",
        "body": (
            "Hi {name},\n\nOpen this link to choose a new password:\n{link}\n\n"
            "If you didn't ask for this, ignore this email."
        ),
    },
}
