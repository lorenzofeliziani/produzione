from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Utenti

from django.contrib.auth.signals import user_logged_in
from .utils import calcola_data_consegna, riformatta_date
from .views import aggiorna_dati, select_ordini, get_ordini_preferences, group

@receiver(user_logged_in)
def on_user_login(sender, request, user, **kwargs):
    try:
        utente = Utenti.objects.get(id=user.id)
        nome_utente = utente.nome if utente else None
        ruolo_utente = utente.ruolo.ruolo if utente else None
        
        # Esegui aggiornamento dati SOLO se ruolo richiesto
        if ruolo_utente in ["Amministratore", "Pianificazione"]:
            aggiorna_dati(request)  # se aggiorna_dati usa il request, ok; altrimenti va modificata

        # Calcola avanzamento ordini
        avanzamento_ordini, ordini_da_pianificare, storico_ordini = select_ordini(request, ruolo_utente)
        avanzamento_ordini_preferences = get_ordini_preferences(avanzamento_ordini)
        ordini_da_pianificare_preferences = get_ordini_preferences(ordini_da_pianificare)
        storico_ordini_preferences = get_ordini_preferences(storico_ordini)
        avanzamento_ordini_groups = group(avanzamento_ordini)
        ordini_da_pianificare_groups = group(ordini_da_pianificare)
        storico_ordini_groups = group(storico_ordini)        

        # Salva i dati in sessione (puoi anche serializzare se necessario)
        request.session['avanzamento_ordini'] = avanzamento_ordini 
        request.session['ordini_da_pianificare'] = ordini_da_pianificare
        request.session['storico_ordini'] = storico_ordini
        request.session['avanzamento_ordini_preferences'] = avanzamento_ordini_preferences
        request.session['ordini_da_pianificare_preferences'] = ordini_da_pianificare_preferences
        request.session['storico_ordini_preferences'] = storico_ordini_preferences
        request.session['avanzamento_ordini_groups'] = avanzamento_ordini_groups
        request.session['ordini_da_pianificare_groups'] = ordini_da_pianificare_groups
        request.session['storico_ordini_groups'] = storico_ordini_groups
        request.session['ruolo_utente'] = ruolo_utente
        request.session['nome_utente'] = nome_utente

    except Exception as e:
        import traceback
        traceback.print_exc()


@receiver(post_save, sender=User)
def crea_profilo(sender, instance, created, **kwargs):
    if created:
        Utenti.objects.create(user=instance)
