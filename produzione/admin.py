from django.contrib import admin
from .models import Utenti

@admin.register(Utenti)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('username', 'ruolo')
    search_fields = ('user__username',)
    list_filter = ('ruolo',)