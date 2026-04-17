from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('exec/', views.sse_view, name='exec'),
]
