from datetime import time

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

from faculty_app.models import ClassRoom, MasterFaculty, Section, Teacher
from student_app.models import Student


class Command(BaseCommand):
    help = "Seed demo data: teachers, sections, students, and classes."

    def add_arguments(self, parser):
        parser.add_argument("--teachers", type=int, default=20)
        parser.add_argument("--sections", type=int, default=10)
        parser.add_argument("--students-per-section", type=int, default=40)
        parser.add_argument("--subjects-per-section", type=int, default=5)
        parser.add_argument("--password", type=str, default="Pass@123")

    @transaction.atomic
    def handle(self, *args, **options):
        teachers_count = options["teachers"]
        sections_count = options["sections"]
        students_per_section = options["students_per_section"]
        subjects_per_section = options["subjects_per_section"]
        password_hash = make_password(options["password"])

        subjects_pool = [
            "Computer Networks",
            "Operating Systems",
            "Database Systems",
            "Software Engineering",
            "Data Structures",
            "Algorithms",
            "Machine Learning",
            "Web Technologies",
            "Compiler Design",
            "Cloud Computing",
        ]

        self.stdout.write("Seeding teachers and master faculty...")
        teachers = []
        for i in range(1, teachers_count + 1):
            enrollment_id = f"TCH{i:04d}"
            email = f"{enrollment_id.lower()}@kiit.ac.in"
            name = f"Teacher {i:02d}"

            master, _ = MasterFaculty.objects.update_or_create(
                enrollment_id=enrollment_id,
                defaults={
                    "name": name,
                    "email": email,
                    "department": "CSE",
                    "designation": "Assistant Professor",
                },
            )

            user, _ = User.objects.update_or_create(
                username=enrollment_id,
                defaults={"email": email, "password": password_hash},
            )

            teacher, _ = Teacher.objects.update_or_create(
                enrollment_id=enrollment_id,
                defaults={
                    "user": user,
                    "name": master.name,
                    "department": master.department,
                    "designation": master.designation,
                    "mail_verified": True,
                    "is_registered": True,
                },
            )
            teachers.append(teacher)

        self.stdout.write("Seeding sections...")
        sections = []
        for i in range(1, sections_count + 1):
            section, _ = Section.objects.update_or_create(
                code=f"CSE-{i:02d}",
                defaults={
                    "name": f"Computer Science Section {i:02d}",
                    "expected_strength": students_per_section,
                    "is_active": True,
                },
            )
            sections.append(section)

        self.stdout.write("Seeding students...")
        roll_seed = 2300000
        created_students = 0
        for section_index, section in enumerate(sections, start=1):
            for student_index in range(1, students_per_section + 1):
                roll = roll_seed + (section_index * 1000) + student_index
                username = str(roll)
                email = f"{roll}@kiit.ac.in"
                name = f"Student S{section_index:02d}-{student_index:02d}"

                user, _ = User.objects.update_or_create(
                    username=username,
                    defaults={"email": email, "password": password_hash},
                )

                Student.objects.update_or_create(
                    roll=roll,
                    defaults={
                        "name": name,
                        "user": user,
                        "section": section,
                        "mail_verified": True,
                        "face_verified": False,
                    },
                )
                created_students += 1

        self.stdout.write("Seeding class cards...")
        created_classes = 0
        for section_i, section in enumerate(sections):
            for j in range(subjects_per_section):
                teacher = teachers[(section_i + j) % len(teachers)]
                subject_name = subjects_pool[j % len(subjects_pool)]
                ClassRoom.objects.update_or_create(
                    section=section,
                    subject_name=subject_name,
                    defaults={
                        "teacher": teacher,
                        "start_time": time(9 + (j % 5), 0),
                        "end_time": time(10 + (j % 5), 0),
                        "is_active": True,
                    },
                )
                created_classes += 1

        self.stdout.write(self.style.SUCCESS("Demo dataset ready."))
        self.stdout.write(
            self.style.SUCCESS(
                f"Teachers: {teachers_count}, Sections: {sections_count}, "
                f"Students: {created_students}, Classes: {created_classes}"
            )
        )
