from django.contrib import admin
from .models import Student


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'roll',
        'mail_verified',
        'face_verified',
        'is_verified',
    )

    search_fields = (
        'user__username',
        'user__email',
        'roll',
    )

    list_filter = (
        'mail_verified',
        'face_verified',
    )

    ordering = ('roll',)
