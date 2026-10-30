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
    Ensure migrations and static files are executed even if the user's
    build command on Render only ran 'pip install -r requirements.txt'.
    """
    print("==> Gunicorn on_starting: Verifying database migrations...")
    try:
        subprocess.run([sys.executable, "manage.py", "migrate", "--noinput"], check=False)
    except Exception as e:
        print(f"Warning: automatic startup migrate skipped: {e}")

    print("==> Gunicorn on_starting: Verifying static files...")
    try:
        subprocess.run([sys.executable, "manage.py", "collectstatic", "--noinput"], check=False)
    except Exception as e:
        print(f"Warning: automatic startup collectstatic skipped: {e}")
