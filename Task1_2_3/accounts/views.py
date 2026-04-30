import json

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import api_view

from .models import Activity, Comment, Image, Post, Profile, UserData


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


def _post_payload(post):
    return {
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "author": post.author.username,
        "created_at": post.created_at.isoformat(),
        "updated_at": post.updated_at.isoformat(),
    }


def _image_payload(image):
    image_url = image.image.url if image.image else None
    return {
        "id": image.id,
        "title": image.title,
        "image": image_url,
        "uploaded_by": image.uploaded_by.username,
        "post": image.post_id,
        "uploaded_at": image.uploaded_at.isoformat(),
    }


def _comment_payload(comment):
    return {
        "id": comment.id,
        "content": comment.content,
        "author": comment.author.username,
        "post": comment.post_id,
        "created_at": comment.created_at.isoformat(),
        "updated_at": comment.updated_at.isoformat(),
    }


def _activity_payload(activity):
    return {
        "id": activity.id,
        "user": activity.user.username,
        "action_type": activity.action_type,
        "target_id": activity.target_id,
        "target_type": activity.target_type,
        "created_at": activity.created_at.isoformat(),
    }


def _paginate(queryset, page_number, per_page=10):
    paginator = Paginator(queryset, per_page)
    page_obj = paginator.get_page(page_number)
    return paginator, page_obj


def _send_notification_email(recipient, subject, body):
    if not recipient or not recipient.email:
        return

    user_data, _ = UserData.objects.get_or_create(user=recipient)
    if not user_data.email_notifications_enabled:
        return

    send_mail(
        subject=subject,
        message=body,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@example.com"),
        recipient_list=[recipient.email],
        fail_silently=False,
    )


def _resolve_activity_target_owner(target_type, target_id):
    if target_type == Activity.TARGET_TYPE_POST:
        try:
            return Post.objects.select_related("author").get(pk=target_id).author
        except Post.DoesNotExist:
            return None

    if target_type == Activity.TARGET_TYPE_COMMENT:
        try:
            return Comment.objects.select_related("author").get(pk=target_id).author
        except Comment.DoesNotExist:
            return None

    return None


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


@require_authenticated_user
@require_POST
def create_post_view(request):
    data = _parse_json_body(request)
    if not data:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    title = data.get("title", "").strip()
    content = data.get("content", "").strip()

    if not title or not content:
        return JsonResponse({"error": "title and content are required"}, status=400)

    post = Post.objects.create(title=title, content=content, author=request.user)
    return JsonResponse({"message": "Post created successfully", "post": _post_payload(post)}, status=201)


@require_GET
def list_posts_view(request):
    posts = Post.objects.select_related("author").all()
    return JsonResponse({"posts": [_post_payload(post) for post in posts]})


@require_GET
def view_post_view(request, post_id):
    try:
        post = Post.objects.select_related("author").get(pk=post_id)
    except Post.DoesNotExist:
        return JsonResponse({"error": "Post not found"}, status=404)

    return JsonResponse({"post": _post_payload(post)})


@require_authenticated_user
@require_http_methods(["POST", "PUT", "PATCH"])
def update_post_view(request, post_id):
    try:
        post = Post.objects.get(pk=post_id)
    except Post.DoesNotExist:
        return JsonResponse({"error": "Post not found"}, status=404)

    if post.author_id != request.user.id:
        return JsonResponse({"error": "Only the author can update this post"}, status=403)

    data = _parse_json_body(request)
    if not data:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    title = data.get("title")
    content = data.get("content")

    if title is not None:
        title = title.strip()
        if not title:
            return JsonResponse({"error": "title cannot be empty"}, status=400)
        post.title = title

    if content is not None:
        content = content.strip()
        if not content:
            return JsonResponse({"error": "content cannot be empty"}, status=400)
        post.content = content

    if title is None and content is None:
        return JsonResponse({"error": "At least one of title or content is required"}, status=400)

    post.save()
    return JsonResponse({"message": "Post updated successfully", "post": _post_payload(post)})


@require_authenticated_user
@require_http_methods(["POST", "DELETE"])
def delete_post_view(request, post_id):
    try:
        post = Post.objects.get(pk=post_id)
    except Post.DoesNotExist:
        return JsonResponse({"error": "Post not found"}, status=404)

    if post.author_id != request.user.id:
        return JsonResponse({"error": "Only the author can delete this post"}, status=403)

    post.delete()
    return JsonResponse({"message": "Post deleted successfully"})


@require_authenticated_user
@require_POST
def upload_image_view(request):
    title = request.POST.get("title", "").strip()
    image_file = request.FILES.get("image")
    post_id = request.POST.get("post")

    if not title:
        return JsonResponse({"error": "title is required"}, status=400)
    if not image_file:
        return JsonResponse({"error": "image file is required"}, status=400)

    post = None
    if post_id:
        try:
            post = Post.objects.get(pk=post_id)
        except Post.DoesNotExist:
            return JsonResponse({"error": "Post not found"}, status=404)

    image = Image.objects.create(
        title=title,
        image=image_file,
        uploaded_by=request.user,
        post=post,
    )
    return JsonResponse({"message": "Image uploaded successfully", "image": _image_payload(image)}, status=201)


@require_GET
def list_images_view(request):
    page_number = request.GET.get("page", "1")
    images = Image.objects.select_related("uploaded_by", "post").all()

    paginator = Paginator(images, 10)
    page_obj = paginator.get_page(page_number)

    return JsonResponse(
        {
            "page": page_obj.number,
            "total_pages": paginator.num_pages,
            "total_items": paginator.count,
            "images": [_image_payload(image) for image in page_obj.object_list],
        }
    )


@require_GET
def view_image_view(request, image_id):
    try:
        image = Image.objects.select_related("uploaded_by", "post").get(pk=image_id)
    except Image.DoesNotExist:
        return JsonResponse({"error": "Image not found"}, status=404)

    return JsonResponse({"image": _image_payload(image)})


@require_authenticated_user
@require_http_methods(["POST", "PUT", "PATCH"])
def update_image_view(request, image_id):
    try:
        image = Image.objects.get(pk=image_id)
    except Image.DoesNotExist:
        return JsonResponse({"error": "Image not found"}, status=404)

    if image.uploaded_by_id != request.user.id:
        return JsonResponse({"error": "Only the uploader can update this image"}, status=403)

    title = request.POST.get("title")
    post_id = request.POST.get("post")
    new_image_file = request.FILES.get("image")

    has_change = False

    if title is not None:
        title = title.strip()
        if not title:
            return JsonResponse({"error": "title cannot be empty"}, status=400)
        image.title = title
        has_change = True

    if post_id is not None:
        if post_id == "":
            image.post = None
            has_change = True
        else:
            try:
                image.post = Post.objects.get(pk=post_id)
                has_change = True
            except Post.DoesNotExist:
                return JsonResponse({"error": "Post not found"}, status=404)

    if new_image_file is not None:
        image.image = new_image_file
        has_change = True

    if not has_change:
        return JsonResponse({"error": "No valid fields provided for update"}, status=400)

    image.save()
    return JsonResponse({"message": "Image updated successfully", "image": _image_payload(image)})


@require_authenticated_user
@require_http_methods(["POST", "DELETE"])
def delete_image_view(request, image_id):
    try:
        image = Image.objects.get(pk=image_id)
    except Image.DoesNotExist:
        return JsonResponse({"error": "Image not found"}, status=404)

    if image.uploaded_by_id != request.user.id:
        return JsonResponse({"error": "Only the uploader can delete this image"}, status=403)

    image.delete()
    return JsonResponse({"message": "Image deleted successfully"})


comment_request_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["content", "post"],
    properties={
        "content": openapi.Schema(type=openapi.TYPE_STRING),
        "post": openapi.Schema(type=openapi.TYPE_INTEGER),
    },
)

comment_update_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["content"],
    properties={"content": openapi.Schema(type=openapi.TYPE_STRING)},
)

activity_request_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["action_type", "target_type", "target_id"],
    properties={
        "action_type": openapi.Schema(type=openapi.TYPE_STRING, enum=[choice[0] for choice in Activity.ACTION_CHOICES]),
        "target_type": openapi.Schema(type=openapi.TYPE_STRING, enum=[choice[0] for choice in Activity.TARGET_CHOICES]),
        "target_id": openapi.Schema(type=openapi.TYPE_INTEGER),
    },
)

notification_toggle_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "email_notifications_enabled": openapi.Schema(type=openapi.TYPE_BOOLEAN),
    },
)


@swagger_auto_schema(method="post", request_body=comment_request_schema, operation_summary="Create a comment")
@api_view(["POST"])
def create_comment_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)

    content = str(request.data.get("content", "")).strip()
    post_id = request.data.get("post")

    if not content or post_id is None or post_id == "":
        return JsonResponse({"error": "content and post are required"}, status=400)

    try:
        post_id_int = int(post_id)
    except (TypeError, ValueError):
        return JsonResponse({"error": "post must be an integer primary key", "post": post_id}, status=400)

    try:
        post = Post.objects.select_related("author").get(pk=post_id_int)
    except Post.DoesNotExist:
        return JsonResponse(
            {"error": "Post not found", "post": post_id_int, "hint": "Use GET /posts/ or create one via POST /posts/create/."},
            status=404,
        )

    comment = Comment.objects.create(content=content, author=request.user, post=post)
    activity = Activity.objects.create(
        user=request.user,
        action_type=Activity.ACTION_TYPE_COMMENT,
        target_id=post.id,
        target_type=Activity.TARGET_TYPE_POST,
    )

    if post.author_id != request.user.id:
        _send_notification_email(
            recipient=post.author,
            subject="New comment on your post",
            body=f"{request.user.username} commented on your post '{post.title}'.",
        )

    return JsonResponse(
        {
            "message": "Comment created successfully",
            "comment": _comment_payload(comment),
            "activity": _activity_payload(activity),
        },
        status=201,
    )


@swagger_auto_schema(
    method="get",
    manual_parameters=[
        openapi.Parameter("page", openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
        openapi.Parameter("page_size", openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
        openapi.Parameter("post", openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
    ],
    operation_summary="List comments with pagination",
)
@api_view(["GET"])
def list_comments_view(request):
    comments = Comment.objects.select_related("author", "post").all()
    post_id = request.GET.get("post")
    if post_id:
        comments = comments.filter(post_id=post_id)

    page_number = request.GET.get("page", "1")
    page_size = request.GET.get("page_size", "10")
    try:
        page_size = max(1, min(int(page_size), 50))
    except (TypeError, ValueError):
        page_size = 10

    paginator, page_obj = _paginate(comments, page_number, page_size)
    return JsonResponse(
        {
            "page": page_obj.number,
            "page_size": page_size,
            "total_pages": paginator.num_pages,
            "total_items": paginator.count,
            "comments": [_comment_payload(comment) for comment in page_obj.object_list],
        }
    )


@swagger_auto_schema(
    method="get",
    manual_parameters=[
        openapi.Parameter("q", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=True),
        openapi.Parameter("page", openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
        openapi.Parameter("page_size", openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
    ],
    operation_summary="Search comments by content, author, post title",
)
@api_view(["GET"])
def search_comments_view(request):
    query = request.GET.get("q", "").strip()
    if not query:
        return JsonResponse({"error": "q query parameter is required"}, status=400)

    comments = (
        Comment.objects.select_related("author", "post")
        .filter(Q(content__icontains=query) | Q(author__username__icontains=query) | Q(post__title__icontains=query))
        .distinct()
    )

    page_number = request.GET.get("page", "1")
    page_size = request.GET.get("page_size", "10")
    try:
        page_size = max(1, min(int(page_size), 50))
    except (TypeError, ValueError):
        page_size = 10

    paginator, page_obj = _paginate(comments, page_number, page_size)
    return JsonResponse(
        {
            "query": query,
            "page": page_obj.number,
            "page_size": page_size,
            "total_pages": paginator.num_pages,
            "total_items": paginator.count,
            "comments": [_comment_payload(comment) for comment in page_obj.object_list],
        }
    )


@swagger_auto_schema(method="post", request_body=comment_update_schema, operation_summary="Update own comment")
@api_view(["POST", "PUT", "PATCH"])
def update_comment_view(request, comment_id):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)

    try:
        comment = Comment.objects.select_related("author").get(pk=comment_id)
    except Comment.DoesNotExist:
        return JsonResponse({"error": "Comment not found"}, status=404)

    if comment.author_id != request.user.id:
        return JsonResponse({"error": "Only the author can update this comment"}, status=403)

    content = request.data.get("content")
    if content is None:
        return JsonResponse({"error": "content is required"}, status=400)

    content = str(content).strip()
    if not content:
        return JsonResponse({"error": "content cannot be empty"}, status=400)

    comment.content = content
    comment.save()
    return JsonResponse({"message": "Comment updated successfully", "comment": _comment_payload(comment)})


@swagger_auto_schema(method="delete", operation_summary="Delete own comment")
@swagger_auto_schema(method="post", operation_summary="Delete own comment")
@api_view(["POST", "DELETE"])
def delete_comment_view(request, comment_id):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)

    try:
        comment = Comment.objects.get(pk=comment_id)
    except Comment.DoesNotExist:
        return JsonResponse({"error": "Comment not found"}, status=404)

    if comment.author_id != request.user.id:
        return JsonResponse({"error": "Only the author can delete this comment"}, status=403)

    comment.delete()
    return JsonResponse({"message": "Comment deleted successfully"})


@swagger_auto_schema(method="post", request_body=activity_request_schema, operation_summary="Create activity event")
@api_view(["POST"])
def create_activity_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)

    action_type = request.data.get("action_type")
    target_type = request.data.get("target_type")
    target_id = request.data.get("target_id")

    valid_actions = {choice[0] for choice in Activity.ACTION_CHOICES}
    valid_targets = {choice[0] for choice in Activity.TARGET_CHOICES}

    if action_type not in valid_actions:
        return JsonResponse({"error": f"action_type must be one of {sorted(valid_actions)}"}, status=400)
    if target_type not in valid_targets:
        return JsonResponse({"error": f"target_type must be one of {sorted(valid_targets)}"}, status=400)
    if not target_id:
        return JsonResponse({"error": "target_id is required"}, status=400)

    try:
        target_id = int(target_id)
    except (TypeError, ValueError):
        return JsonResponse({"error": "target_id must be an integer"}, status=400)

    target_owner = _resolve_activity_target_owner(target_type, target_id)
    if target_owner is None:
        return JsonResponse({"error": "Target not found"}, status=404)

    activity = Activity.objects.create(
        user=request.user,
        action_type=action_type,
        target_type=target_type,
        target_id=target_id,
    )

    if action_type == Activity.ACTION_TYPE_LIKE and target_owner.id != request.user.id:
        _send_notification_email(
            recipient=target_owner,
            subject="Your content received a like",
            body=f"{request.user.username} liked your {target_type}.",
        )

    return JsonResponse({"message": "Activity created successfully", "activity": _activity_payload(activity)}, status=201)


@swagger_auto_schema(
    method="get",
    manual_parameters=[
        openapi.Parameter("page", openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
        openapi.Parameter("page_size", openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
    ],
    operation_summary="List current user activities",
)
@api_view(["GET"])
def list_activities_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)

    activities = Activity.objects.select_related("user").filter(user=request.user)
    page_number = request.GET.get("page", "1")
    page_size = request.GET.get("page_size", "10")
    try:
        page_size = max(1, min(int(page_size), 50))
    except (TypeError, ValueError):
        page_size = 10

    paginator, page_obj = _paginate(activities, page_number, page_size)
    return JsonResponse(
        {
            "page": page_obj.number,
            "page_size": page_size,
            "total_pages": paginator.num_pages,
            "total_items": paginator.count,
            "activities": [_activity_payload(activity) for activity in page_obj.object_list],
        }
    )


@swagger_auto_schema(method="post", request_body=notification_toggle_schema, operation_summary="Toggle email notifications")
@api_view(["POST"])
def toggle_notification_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)

    user_data, _ = UserData.objects.get_or_create(user=request.user)
    enabled = request.data.get("email_notifications_enabled")

    if enabled is None:
        user_data.email_notifications_enabled = not user_data.email_notifications_enabled
    elif isinstance(enabled, bool):
        user_data.email_notifications_enabled = enabled
    else:
        return JsonResponse({"error": "email_notifications_enabled must be a boolean"}, status=400)

    user_data.save(update_fields=["email_notifications_enabled"])
    return JsonResponse(
        {
            "message": "Notification preference updated",
            "email_notifications_enabled": user_data.email_notifications_enabled,
        }
    )
