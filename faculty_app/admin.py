from django.contrib import admin, messages
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.db import transaction
from .models import (
    Attendance,
    AttendanceSession,
    ClassRoom,
    MasterFaculty,
    RollingQRToken,
    Section,
    Teacher,
)


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
    actions = ("create_teacher_accounts",)

    @admin.action(description="Create teacher accounts for selected faculty")
    def create_teacher_accounts(self, request, queryset):
        created = 0
        skipped = 0
        default_password = "Pass@123"
        password_hash = make_password(default_password)

        for master in queryset:
            teacher_exists = Teacher.objects.filter(enrollment_id=master.enrollment_id).exists()
            if teacher_exists:
                skipped += 1
                continue

            user, _ = User.objects.update_or_create(
                username=master.enrollment_id,
                defaults={
                    "email": master.email,
                    "password": password_hash,
                },
            )
            Teacher.objects.create(
                user=user,
                name=master.name,
                enrollment_id=master.enrollment_id,
                department=master.department,
                designation=master.designation,
                mail_verified=True,
                is_registered=True,
            )
            created += 1

        self.message_user(
            request,
            f"Teacher accounts created: {created}, skipped(existing): {skipped}. Default password: {default_password}",
            level=messages.SUCCESS,
        )


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
    actions = ("delete_teachers_with_user_accounts",)

    @admin.action(description="Delete selected teachers and linked user accounts")
    def delete_teachers_with_user_accounts(self, request, queryset):
        ids = list(queryset.values_list("id", flat=True))
        users = list(queryset.values_list("user_id", flat=True))
        ClassRoom.objects.filter(teacher_id__in=ids).delete()
        Teacher.objects.filter(id__in=ids).delete()
        User.objects.filter(id__in=users).delete()
        self.message_user(request, f"Deleted {len(ids)} teachers and linked user accounts.", level=messages.SUCCESS)

    def delete_model(self, request, obj):
        user_id = obj.user_id
        super().delete_model(request, obj)
        User.objects.filter(id=user_id).delete()

    def delete_queryset(self, request, queryset):
        user_ids = list(queryset.values_list("user_id", flat=True))
        super().delete_queryset(request, queryset)
        User.objects.filter(id__in=user_ids).delete()


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "expected_strength", "is_active")
    search_fields = ("code", "name")
    list_filter = ("is_active",)
    actions = ("create_students_up_to_strength",)

    @admin.action(description="Insert students up to expected strength (per selected section)")
    @transaction.atomic
    def create_students_up_to_strength(self, request, queryset):
        from student_app.models import Student

        default_password = "Pass@123"
        password_hash = make_password(default_password)
        max_roll = Student.objects.order_by("-roll").values_list("roll", flat=True).first() or 2300000
        created_total = 0

        for section in queryset:
            current = Student.objects.filter(section=section).count()
            needed = max(section.expected_strength - current, 0)
            for idx in range(1, needed + 1):
                max_roll += 1
                roll = max_roll
                username = str(roll)
                email = f"{roll}@kiit.ac.in"
                student_name = f"Student {section.code}-{current + idx:02d}"

                user = User.objects.create(username=username, email=email, password=password_hash)
                Student.objects.create(
                    user=user,
                    name=student_name,
                    roll=roll,
                    section=section,
                    mail_verified=True,
                    face_verified=False,
                )
                created_total += 1

        self.message_user(
            request,
            f"Inserted {created_total} students. Default password: {default_password}",
            level=messages.SUCCESS,
        )


@admin.register(ClassRoom)
class ClassRoomAdmin(admin.ModelAdmin):
    list_display = ("subject_name", "section", "teacher", "start_time", "end_time", "is_active")
    search_fields = ("subject_name", "section__code", "teacher__name", "teacher__enrollment_id")
    list_filter = ("section", "is_active")


@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "classroom", "teacher", "started_at", "ended_at", "is_live", "qr_validity_seconds")
    search_fields = ("classroom__subject_name", "classroom__section__code", "teacher__enrollment_id")
    list_filter = ("is_live", "session_date")


@admin.register(RollingQRToken)
class RollingQRTokenAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "issued_at", "expires_at", "is_active")
    search_fields = ("token", "session__id")
    list_filter = ("is_active",)


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("session", "student", "status", "qr_scanned_at", "face_checked_at", "marked_at")
    search_fields = ("student__roll", "student__name", "session__id")
    list_filter = ("status",)
