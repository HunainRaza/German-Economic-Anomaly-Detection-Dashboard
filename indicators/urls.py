from django.urls import path
from . import views

app_label = 'indicators'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
]