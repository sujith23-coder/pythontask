import json

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core import mail
from django.test import TestCase

from .models import Activity, Comment, Image, Post, UserData


class BlogApiTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(username="author", password="pass12345")
        self.other_user = User.objects.create_user(username="other", password="pass12345")

    def test_create_post_requires_authentication(self):
        response = self.client.post(
            "/posts/create/",
            data=json.dumps({"title": "New Post", "content": "Post content"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_author_can_update_and_other_user_cannot(self):
        post = Post.objects.create(title="Old", content="Old content", author=self.author)

        self.client.login(username="other", password="pass12345")
        forbidden_response = self.client.post(
            f"/posts/{post.id}/update/",
            data=json.dumps({"title": "Changed"}),
            content_type="application/json",
        )
        self.assertEqual(forbidden_response.status_code, 403)
        self.client.logout()

        self.client.login(username="author", password="pass12345")
        success_response = self.client.post(
            f"/posts/{post.id}/update/",
            data=json.dumps({"title": "Changed"}),
            content_type="application/json",
        )
        self.assertEqual(success_response.status_code, 200)
        post.refresh_from_db()
        self.assertEqual(post.title, "Changed")


class GalleryApiTests(TestCase):
    def setUp(self):
        self.uploader = User.objects.create_user(username="uploader", password="pass12345")
        self.other_user = User.objects.create_user(username="other", password="pass12345")
        self.post = Post.objects.create(title="Reference Post", content="Post content", author=self.uploader)

    def test_upload_image_requires_authentication(self):
        image_file = SimpleUploadedFile("image.jpg", b"image-bytes", content_type="image/jpeg")
        response = self.client.post(
            "/gallery/upload/",
            data={"title": "Image", "image": image_file, "post": self.post.id},
        )
        self.assertEqual(response.status_code, 401)

    def test_uploader_can_delete_and_other_user_cannot(self):
        image = Image.objects.create(
            title="Sample",
            image=SimpleUploadedFile("sample.jpg", b"image-bytes", content_type="image/jpeg"),
            uploaded_by=self.uploader,
            post=self.post,
        )

        self.client.login(username="other", password="pass12345")
        forbidden_response = self.client.post(f"/gallery/{image.id}/delete/")
        self.assertEqual(forbidden_response.status_code, 403)
        self.client.logout()

        self.client.login(username="uploader", password="pass12345")
        success_response = self.client.post(f"/gallery/{image.id}/delete/")
        self.assertEqual(success_response.status_code, 200)
        self.assertFalse(Image.objects.filter(pk=image.id).exists())

    def test_gallery_list_is_paginated_by_ten(self):
        for index in range(12):
            Image.objects.create(
                title=f"Image {index}",
                image=SimpleUploadedFile(f"image{index}.jpg", b"image-bytes", content_type="image/jpeg"),
                uploaded_by=self.uploader,
                post=self.post,
            )

        first_page = self.client.get("/gallery/")
        self.assertEqual(first_page.status_code, 200)
        first_data = first_page.json()
        self.assertEqual(first_data["page"], 1)
        self.assertEqual(len(first_data["images"]), 10)
        self.assertEqual(first_data["total_pages"], 2)

        second_page = self.client.get("/gallery/?page=2")
        self.assertEqual(second_page.status_code, 200)
        second_data = second_page.json()
        self.assertEqual(second_data["page"], 2)
        self.assertEqual(len(second_data["images"]), 2)


class CommentApiTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(username="author", password="pass12345", email="author@example.com")
        self.commenter = User.objects.create_user(username="commenter", password="pass12345")
        self.other_user = User.objects.create_user(username="other", password="pass12345")
        self.post = Post.objects.create(title="Sample post", content="Sample content", author=self.author)

    def test_create_comment_requires_authentication(self):
        response = self.client.post(
            "/comments/create/",
            data=json.dumps({"content": "Nice post", "post": self.post.id}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_author_only_comment_update_and_delete(self):
        comment = Comment.objects.create(content="Original", author=self.commenter, post=self.post)

        self.client.login(username="other", password="pass12345")
        forbidden_update = self.client.post(
            f"/comments/{comment.id}/update/",
            data=json.dumps({"content": "Hack"}),
            content_type="application/json",
        )
        self.assertEqual(forbidden_update.status_code, 403)

        forbidden_delete = self.client.post(f"/comments/{comment.id}/delete/")
        self.assertEqual(forbidden_delete.status_code, 403)
        self.client.logout()

        self.client.login(username="commenter", password="pass12345")
        success_update = self.client.post(
            f"/comments/{comment.id}/update/",
            data=json.dumps({"content": "Updated"}),
            content_type="application/json",
        )
        self.assertEqual(success_update.status_code, 200)

        success_delete = self.client.post(f"/comments/{comment.id}/delete/")
        self.assertEqual(success_delete.status_code, 200)
        self.assertFalse(Comment.objects.filter(pk=comment.id).exists())

    def test_comments_list_pagination_and_search(self):
        for index in range(12):
            Comment.objects.create(
                content=f"Keyword test comment {index}",
                author=self.commenter,
                post=self.post,
            )

        page_one = self.client.get("/comments/?page=1&page_size=10")
        self.assertEqual(page_one.status_code, 200)
        page_one_data = page_one.json()
        self.assertEqual(page_one_data["page"], 1)
        self.assertEqual(len(page_one_data["comments"]), 10)

        search = self.client.get("/comments/search/?q=Keyword&page=1&page_size=5")
        self.assertEqual(search.status_code, 200)
        search_data = search.json()
        self.assertEqual(search_data["total_items"], 12)
        self.assertEqual(len(search_data["comments"]), 5)

    def test_comment_creation_sends_email_to_post_author(self):
        self.client.login(username="commenter", password="pass12345")
        response = self.client.post(
            "/comments/create/",
            data=json.dumps({"content": "Great write-up", "post": self.post.id}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("New comment on your post", mail.outbox[0].subject)
        self.assertIn("commented on your post", mail.outbox[0].body)

    def test_comment_creation_skips_email_when_notifications_disabled(self):
        author_data, _ = UserData.objects.get_or_create(user=self.author)
        author_data.email_notifications_enabled = False
        author_data.save()

        self.client.login(username="commenter", password="pass12345")
        response = self.client.post(
            "/comments/create/",
            data=json.dumps({"content": "Another comment", "post": self.post.id}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(mail.outbox), 0)


class ActivityApiTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="pass12345", email="owner@example.com")
        self.actor = User.objects.create_user(username="actor", password="pass12345")
        self.post = Post.objects.create(title="Owner Post", content="Body", author=self.owner)
        self.comment = Comment.objects.create(content="Owner comment", author=self.owner, post=self.post)

    def test_create_like_activity_sends_email(self):
        self.client.login(username="actor", password="pass12345")
        response = self.client.post(
            "/activities/create/",
            data=json.dumps(
                {
                    "action_type": "like",
                    "target_type": "post",
                    "target_id": self.post.id,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Activity.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("received a like", mail.outbox[0].subject)

    def test_activity_list_is_user_specific_and_paginated(self):
        for index in range(15):
            Activity.objects.create(
                user=self.actor,
                action_type=Activity.ACTION_TYPE_LIKE,
                target_type=Activity.TARGET_TYPE_POST,
                target_id=self.post.id,
            )
        Activity.objects.create(
            user=self.owner,
            action_type=Activity.ACTION_TYPE_COMMENT,
            target_type=Activity.TARGET_TYPE_POST,
            target_id=self.post.id,
        )

        self.client.login(username="actor", password="pass12345")
        response = self.client.get("/activities/?page=1&page_size=10")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total_items"], 15)
        self.assertEqual(len(data["activities"]), 10)

    def test_toggle_notifications_updates_preference(self):
        self.client.login(username="owner", password="pass12345")
        response = self.client.post(
            "/notifications/toggle/",
            data=json.dumps({"email_notifications_enabled": False}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.owner.user_data.refresh_from_db()
        self.assertFalse(self.owner.user_data.email_notifications_enabled)

    def test_create_activity_returns_error_for_invalid_target(self):
        self.client.login(username="actor", password="pass12345")
        response = self.client.post(
            "/activities/create/",
            data=json.dumps(
                {
                    "action_type": "like",
                    "target_type": "post",
                    "target_id": 99999,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)
