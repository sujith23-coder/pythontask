import os
import sys
from pathlib import Path

_django_ready = False


def init_django() -> None:
    global _django_ready
    if _django_ready:
        return
    root = Path(__file__).resolve().parent.parent
    dj_root = root / "django_billing"
    if str(dj_root) not in sys.path:
        sys.path.insert(0, str(dj_root))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "billing_project.settings")
    import django

    django.setup()
    _django_ready = True
