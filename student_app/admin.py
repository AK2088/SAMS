from django.contrib import admin
from django.contrib.auth.models import User
from .models import Student


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'roll',
        'section',
        'mail_verified',
        'face_verified',
        'is_verified',
    )

    search_fields = (
        'user__username',
        'user__email',
        'roll',
        'section__code',
    )

    list_filter = (
        'section',
        'mail_verified',
        'face_verified',
    )

    ordering = ('roll',)
    actions = ("delete_students_with_user_accounts",)

    @admin.action(description="Delete selected students and linked user accounts")
    def delete_students_with_user_accounts(self, request, queryset):
        ids = list(queryset.values_list("id", flat=True))
        user_ids = list(queryset.values_list("user_id", flat=True))
        Student.objects.filter(id__in=ids).delete()
        User.objects.filter(id__in=user_ids).delete()

    def delete_model(self, request, obj):
        user_id = obj.user_id
        super().delete_model(request, obj)
        User.objects.filter(id=user_id).delete()

    def delete_queryset(self, request, queryset):
        user_ids = list(queryset.values_list("user_id", flat=True))
        super().delete_queryset(request, queryset)
        User.objects.filter(id__in=user_ids).delete()
