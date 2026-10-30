from django.contrib.auth.hashers import Argon2PasswordHasher


class Argon2idHasher(Argon2PasswordHasher):
    """Argon2id con el perfil mínimo recomendado por OWASP (19 MiB, 2 pasadas, 1 hilo).

    Los valores por defecto de Django usan unos 100 MB por login, demasiado para un VPS pequeño con
    varios logins a la vez. Los parámetros viajan dentro de cada hash: al subirlos aquí, Django
    vuelve a hashear cada contraseña con los nuevos la próxima vez que esa persona entra.
    """

    time_cost = 2
    memory_cost = 19456  # KiB
    parallelism = 1
