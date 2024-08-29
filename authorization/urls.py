from django.urls import path
from . import views

urlpatterns = [
    path('', views.autorize_main, name='autorize'),
]
