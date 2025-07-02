from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Utenti

from django.contrib.auth.signals import user_logged_in
from .utils import calcola_data_consegna
from .views import aggiorna_dati, select_avanzamento_ordini, get_avanzamento_ordini_preferences

@receiver(user_logged_in)
def on_user_login(sender, request, user, **kwargs):
    try:
        utente = Utenti.objects.get(id=user.id)
        ruolo_utente = utente.ruolo.ruolo if utente else None

        # Esegui aggiornamento dati SOLO se ruolo richiesto
        if ruolo_utente in ["Amministratore", "Pianificazione"]:
            aggiorna_dati(request)  # se aggiorna_dati usa il request, ok; altrimenti va modificata

        # Calcola avanzamento ordini
        avanzamento_ordini = select_avanzamento_ordini(request, ruolo_utente)
        avanzamento_ordini_preferences = get_avanzamento_ordini_preferences(avanzamento_ordini)

        # Salva i dati in sessione (puoi anche serializzare se necessario)
        request.session['avanzamento_ordini'] = avanzamento_ordini  # attenzione a cosa salvi in sessione!
        request.session['avanzamento_ordini_preferences'] = avanzamento_ordini_preferences
        request.session['ruolo_utente'] = ruolo_utente

    except Exception as e:
        import traceback
        traceback.print_exc()


@receiver(post_save, sender=User)
def crea_profilo(sender, instance, created, **kwargs):
    if created:
        Utenti.objects.create(user=instance)
