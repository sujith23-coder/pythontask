import os
import sys
from pathlib import Path

_django_ready = False


def init_django() -> None:
    global _django_ready
    if _django_ready:
        return
    dj_root = Path(__file__).resolve().parent.parent / "django_lms"
    if str(dj_root) not in sys.path:
        sys.path.insert(0, str(dj_root))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lms_project.settings")
    import django

    django.setup()
    _django_ready = True
