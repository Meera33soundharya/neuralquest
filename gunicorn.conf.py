import os
import subprocess
import sys

# Automatically bind to Render's dynamic port, or fallback to 8000
port = os.getenv("PORT", "8000")
bind = f"0.0.0.0:{port}"

# Free-tier RAM optimization (512MB RAM cap)
workers = int(os.getenv("GUNICORN_WORKERS", "1"))
threads = int(os.getenv("GUNICORN_THREADS", "2"))
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))

# Log to stdout/stderr so Render captures everything in dashboard logs
accesslog = "-"
errorlog = "-"
loglevel = "info"

def on_starting(server):
    """
    Ensure migrations, static files, and admin account exist on startup.
    """
    print("==> Gunicorn on_starting: Verifying database migrations...")
    try:
        subprocess.run([sys.executable, "manage.py", "migrate", "--noinput"], check=False)
    except Exception as e:
        print(f"Warning: automatic startup migrate skipped: {e}")

    print("==> Gunicorn on_starting: Verifying default administrator user...")
    try:
        seed_cmd = (
            "from django.contrib.auth.models import User; "
            "from rest_framework.authtoken.models import Token; "
            "u, _ = User.objects.get_or_create(username='admin', defaults={'email': 'admin@neuralquest.io'}); "
            "u.set_password('admin123'); u.is_superuser = True; u.is_staff = True; u.save(); "
            "Token.objects.get_or_create(user=u)"
        )
        subprocess.run([sys.executable, "manage.py", "shell", "-c", seed_cmd], check=False)
    except Exception as e:
        print(f"Warning: automatic startup admin creation skipped: {e}")

    print("==> Gunicorn on_starting: Verifying static files...")
    try:
        subprocess.run([sys.executable, "manage.py", "collectstatic", "--noinput"], check=False)
    except Exception as e:
        print(f"Warning: automatic startup collectstatic skipped: {e}")
