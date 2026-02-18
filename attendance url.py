from django.urls import path
from . import views

urlpatterns = [
    path("", views.create_session, name="create_session"),
    path("session/<uuid:session_id>/", views.session_page, name="session_page"),
    path("mark/", views.mark_attendance, name="mark_attendance"),
    path("export/<uuid:session_id>/", views.export_excel, name="export_excel"),
]