from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('<str:playlist_id>/', views.playlist, name='playlist'),
    path('/create_playlist/', views.create_playlist, name='create_playlist')
]
