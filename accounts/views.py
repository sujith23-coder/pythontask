import json

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .models import Profile


def _parse_json_body(request):
    try:
        return json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def require_authenticated_user(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required"}, status=401)
        return view_func(request, *args, **kwargs)

    return wrapper


@csrf_exempt
@require_POST
def signup_view(request):
    data = _parse_json_body(request)
    if not data:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    username = data.get("username", "").strip()
    password = data.get("password", "")
    email = data.get("email", "").strip()

    if not username or not password:
        return JsonResponse({"error": "username and password are required"}, status=400)

    if User.objects.filter(username=username).exists():
        return JsonResponse({"error": "Username already exists"}, status=400)

    user = User.objects.create_user(username=username, password=password, email=email)
    Profile.objects.get_or_create(user=user)
    return JsonResponse({"message": "User created successfully"}, status=201)


@csrf_exempt
@require_POST
def login_view(request):
    data = _parse_json_body(request)
    if not data:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return JsonResponse({"error": "username and password are required"}, status=400)

    user = authenticate(request, username=username, password=password)
    if user is None:
        return JsonResponse({"error": "Invalid username or password"}, status=401)

    login(request, user)
    return JsonResponse({"message": "Login successful"})


@csrf_exempt
@require_POST
def logout_view(request):
    logout(request)
    return JsonResponse({"message": "Logout successful"})


@require_authenticated_user
@require_GET
def profile_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    picture_url = profile.profile_picture.url if profile.profile_picture else None

    return JsonResponse(
        {
            "username": request.user.username,
            "email": request.user.email,
            "additional_details": profile.additional_details,
            "profile_picture": picture_url,
        }
    )


@csrf_exempt
@require_authenticated_user
@require_POST
def update_profile_view(request):
    data = _parse_json_body(request)
    if not data:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    new_username = data.get("username")
    new_email = data.get("email")
    new_details = data.get("additional_details")

    if new_username:
        new_username = new_username.strip()
        if new_username != request.user.username and User.objects.filter(username=new_username).exists():
            return JsonResponse({"error": "Username already exists"}, status=400)
        request.user.username = new_username

    if new_email is not None:
        request.user.email = new_email.strip()

    request.user.save()

    profile, _ = Profile.objects.get_or_create(user=request.user)
    if new_details is not None:
        profile.additional_details = new_details
        profile.save()

    return JsonResponse({"message": "Profile updated successfully"})


@csrf_exempt
@require_authenticated_user
@require_POST
def change_password_view(request):
    data = _parse_json_body(request)
    if not data:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    old_password = data.get("old_password", "")
    new_password = data.get("new_password", "")

    if not old_password or not new_password:
        return JsonResponse({"error": "old_password and new_password are required"}, status=400)

    if not request.user.check_password(old_password):
        return JsonResponse({"error": "Old password is incorrect"}, status=400)

    request.user.set_password(new_password)
    request.user.save()
    login(request, request.user)
    return JsonResponse({"message": "Password changed successfully"})


@csrf_exempt
@require_authenticated_user
@require_POST
def upload_profile_photo_view(request):
    image_file = request.FILES.get("profile_picture")
    if not image_file:
        return JsonResponse({"error": "profile_picture file is required"}, status=400)

    profile, _ = Profile.objects.get_or_create(user=request.user)
    profile.profile_picture = image_file
    profile.save()

    return JsonResponse({"message": "Profile picture updated successfully"})
