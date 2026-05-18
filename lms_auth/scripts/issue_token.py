"""Issue a JWT for local testing: python scripts/issue_token.py faculty1"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "django_lms"))

from app.auth_utils import create_access_token
from app.django_bridge import init_django

init_django()

from django.contrib.auth.models import User  # noqa: E402


def main():
    username = sys.argv[1] if len(sys.argv) > 1 else "faculty1"
    user = User.objects.filter(username=username).first()
    if not user:
        print(f"User '{username}' not found. Run: python manage.py load_sample_data")
        sys.exit(1)
    token = create_access_token(user.id)
    print(token)


if __name__ == "__main__":
    main()
