from django.urls import path

from . import views


urlpatterns = [
    path("", views.home, name="public_home"),
    path("solutions/", views.solutions, name="public_solutions"),
]
