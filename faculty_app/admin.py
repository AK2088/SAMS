from django.contrib import admin
from .models import MasterFaculty, Teacher


@admin.register(MasterFaculty)
class MasterFacultyAdmin(admin.ModelAdmin):
    list_display = (
        'enrollment_id',
        'name',
        'email',
        'department',
        'designation',
    )

    search_fields = (
        'enrollment_id',
        'name',
        'email',
        'department',
    )

    list_filter = ('department', 'designation')


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'name',
        'enrollment_id',
        'department',
        'designation',
        'mail_verified',
    )
