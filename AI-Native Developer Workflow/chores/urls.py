from django.urls import path

from . import views

app_name = "chores"

urlpatterns = [
    path("", views.home, name="home"),
    path("mode/", views.switch_mode, name="switch_mode"),
    path("chores/new/", views.create_chore, name="create_chore"),
    path("chores/<int:pk>/complete/", views.complete_chore, name="complete_chore"),
    path("chores/<int:pk>/review/", views.review_overdue_chore, name="review_overdue_chore"),
]