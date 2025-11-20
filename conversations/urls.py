from django.urls import path
from . import views

urlpatterns = [
    path('memory_lane/', views.memory_lane, name='memory_lane'),
    path('stream/', views.stream, name='stream'),
    path('api/recent_messages/', views.recent_messages, name='recent_messages'),
    path('api/messages/', views.api_messages, name='api_messages'),
    path('api/all_messages/', views.all_messages, name='all_messages'),
]
