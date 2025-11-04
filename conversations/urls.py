from django.urls import path
from . import views

urlpatterns = [
    path('memory_lane/', views.memory_lane, name='memory_lane'),
    path('api/messages/', views.api_messages, name='api_messages'),
    path('api/all_messages/', views.all_messages, name='all_messages'),
    path('api/messages_since/<str:message_id>/', views.messages_since, name='messages_since'),
]
