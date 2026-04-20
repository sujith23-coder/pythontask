from django.contrib import admin
from .models import Activity, Comment, Image, Post, Profile, UserData

admin.site.register(Profile)
admin.site.register(UserData)
admin.site.register(Post)
admin.site.register(Image)
admin.site.register(Comment)
admin.site.register(Activity)
