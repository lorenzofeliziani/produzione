# produzione/urls.py
from django.urls import path
from . import views
from django.contrib.auth import views as auth_views


urlpatterns = [
    path('', views.dashboard, name='dashboard'), 
    path('login/', auth_views.LoginView.as_view(template_name='produzione/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('cambia-password/', views.cambia_password, name='cambia_password'),
    path('avanzamento_ordini/', views.avanzamento_ordini, name='avanzamento_ordini'),
    path('ordini_da_pianificare/', views.ordini_da_pianificare, name='ordini_da_pianificare'),
    path('storico_ordini/', views.storico_ordini, name='storico_ordini'),
    path('tabelle/', views.tabelle, name='tabelle'),
]

