from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    profile_picture = models.ImageField(upload_to="profile_pictures/", blank=True, null=True)
    additional_details = models.TextField(blank=True)

    def __str__(self):
        return f"{self.user.username} Profile"


class UserData(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="user_data")
    email_notifications_enabled = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} UserData"


@receiver(post_save, sender=User)
def create_or_update_user_related_records(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
        UserData.objects.create(user=instance)
        return

    Profile.objects.get_or_create(user=instance)
    UserData.objects.get_or_create(user=instance)


class Post(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="posts")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class Image(models.Model):
    title = models.CharField(max_length=255)
    image = models.ImageField(upload_to="gallery_images/")
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="images")
    post = models.ForeignKey(
        Post,
        on_delete=models.SET_NULL,
        related_name="images",
        null=True,
        blank=True,
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.title


class Comment(models.Model):
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Comment #{self.id} by {self.author.username}"


class Activity(models.Model):
    ACTION_TYPE_COMMENT = "comment"
    ACTION_TYPE_LIKE = "like"
    ACTION_CHOICES = (
        (ACTION_TYPE_COMMENT, "Comment"),
        (ACTION_TYPE_LIKE, "Like"),
    )

    TARGET_TYPE_POST = "post"
    TARGET_TYPE_COMMENT = "comment"
    TARGET_CHOICES = (
        (TARGET_TYPE_POST, "Post"),
        (TARGET_TYPE_COMMENT, "Comment"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="activities")
    action_type = models.CharField(max_length=20, choices=ACTION_CHOICES)
    target_id = models.PositiveBigIntegerField()
    target_type = models.CharField(max_length=20, choices=TARGET_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} {self.action_type} {self.target_type}#{self.target_id}"
