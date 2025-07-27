import traceback
import copy
from datetime import date
from collections import defaultdict
from .utils import calcola_data_consegna, riformatta_date, riformatta_date_groups
from datetime import datetime
from django.shortcuts import redirect
from django.db import connection, transaction
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Avanzamento_Ordini, Utenti, Note, Note_Ordini, Profili_Stati, Profili, Stati_Ordini
from dati.sage.connect import bsdb04_connection
try:
    from produzione import constant
except:
    import constant


@login_required(login_url='login')
def dashboard(request):
    ruolo_utente = request.session.get('ruolo_utente')
    nome_utente = request.session.get('nome_utente')
    context = {
        'ruolo_utente': ruolo_utente,
        'nome_utente': nome_utente
    }
    
    return render(request, 'produzione/dashboard.html', context)

@login_required(login_url='login')
def avanzamento_ordini(request):
    modalita = request.GET.get('modalita', 'standard')
    ordine_filtro   = request.GET.get("ordine_filtro", "")
    cliente_filtro   = request.GET.get("cliente_filtro", "")
    stato_filtro     = request.GET.get("stato_filtro", "")
    operatore_filtro = request.GET.get("operatore_filtro", "")
    articolo_filtro = request.GET.get("articolo_filtro", "")
    old_code_filtro = request.GET.get("old_code_filtro", "")
    avanzamento_ordini = request.session.get('avanzamento_ordini')
    ordini_da_pianificare = request.session.get('ordini_da_pianificare')
    avanzamento_ordini_preferences = request.session.get('avanzamento_ordini_preferences')
    ordini_da_pianificare_preferences = request.session.get('ordini_da_pianificare_preferences')
    avanzamento_ordini_groups = request.session.get('avanzamento_ordini_groups')
    ordini_da_pianificare_groups = request.session.get('ordini_da_pianificare_groups')
    ruolo_utente = request.session.get('ruolo_utente')
    nome_utente = request.session['nome_utente']
    
    stati_ordini = list(
    Stati_Ordini.objects.values_list('stato', flat=True).distinct().order_by('stato')
        )

    operatori = list(
        Utenti.objects.filter(is_operatore=True).values_list('nome', flat=True).distinct().order_by('nome')
        )

    if request.method == 'POST':
        action = request.POST.get('form_type')
        modalita = request.GET.get('modalita', 'standard')
        ordine_filtro   = request.GET.get("ordine_filtro", "")
        cliente_filtro   = request.GET.get("cliente_filtro", "")
        stato_filtro     = request.GET.get("stato_filtro", "")
        operatore_filtro = request.GET.get("operatore_filtro", "")
        articolo_filtro = request.GET.get("articolo_filtro", "")
        old_code_filtro = request.GET.get("old_code_filtro", "")
        if action == "general_update":
            if ruolo_utente in ["Amministratore", "Pianificazione"]:
                aggiorna_dati(request)
            avanzamento_ordini, ordini_da_pianificare, storico_ordini = select_ordini(request, ruolo_utente)
            avanzamento_ordini_preferences = get_ordini_preferences(avanzamento_ordini)
            ordini_da_pianificare_preferences = get_ordini_preferences(ordini_da_pianificare)
            storico_ordini_preferences = get_ordini_preferences(storico_ordini)
            avanzamento_ordini_groups = group(avanzamento_ordini)
            ordini_da_pianificare_groups = group(ordini_da_pianificare)
            storico_ordini_groups = group(storico_ordini)        

            request.session['avanzamento_ordini'] = avanzamento_ordini 
            request.session['ordini_da_pianificare'] = ordini_da_pianificare
            request.session['storico_ordini'] = storico_ordini
            request.session['avanzamento_ordini_preferences'] = avanzamento_ordini_preferences
            request.session['ordini_da_pianificare_preferences'] = ordini_da_pianificare_preferences
            request.session['storico_ordini_preferences'] = storico_ordini_preferences
            request.session['avanzamento_ordini_groups'] = avanzamento_ordini_groups
            request.session['ordini_da_pianificare_groups'] = ordini_da_pianificare_groups
            request.session['storico_ordini_groups'] = storico_ordini_groups
        
        elif action == "update_ord_list":
            try:
                numero_ordine = request.POST.get('ordine')
                nuovo_operatore_nome = request.POST.get('operatore')
                nuovo_stato_nome = request.POST.get('stato')
                
                stato_obj = Stati_Ordini.objects.filter(stato=nuovo_stato_nome).first()
                operatore_obj = Utenti.objects.filter(nome=nuovo_operatore_nome).first()
                
                ordini_selezionati = Avanzamento_Ordini.objects.filter(ordine=numero_ordine)

                adv_idx   = {(o['sede'], o['ordine'], o['n_riga']): o for o in avanzamento_ordini}
                pian_idx  = {(o['sede'], o['ordine'], o['n_riga']): o for o in ordini_da_pianificare}

                for row in ordini_selezionati:
                    k = (row.sede, row.ordine, row.n_riga)

                    if row.stato_ord.stato == "Da pianificare" and stato_obj.stato != "Da pianificare":
                        pian_idx.pop(k, None)
                    elif row.stato_ord.stato != "Da pianificare" and stato_obj.stato == "Da pianificare":
                        pian_idx[k] = adv_idx[k] 

                ordini_da_pianificare = list(pian_idx.values())

                # Aggiorna il DB
                ordini_selezionati.update(
                    operatore=operatore_obj,
                    stato_ord=stato_obj
                )

                # Aggiorna la sessione di avanzamento_ordini
                for ordine in avanzamento_ordini:
                    if ordine['ordine'] == numero_ordine:
                        ordine['operatore'] = operatore_obj.username if operatore_obj else None
                        ordine['des_operatore'] = operatore_obj.nome if operatore_obj else None
                        ordine['id_stato_ord'] = stato_obj.id if stato_obj else None
                        ordine['des_stato_ord'] = stato_obj.stato if stato_obj else None

                # Salva in sessione
                avanzamento_ordini_preferences = get_ordini_preferences(avanzamento_ordini)
                ordini_da_pianificare_preferences = get_ordini_preferences(ordini_da_pianificare)        
                avanzamento_ordini_groups = group(avanzamento_ordini)
                ordini_da_pianificare_groups = group(ordini_da_pianificare)      

                request.session['avanzamento_ordini_groups'] = avanzamento_ordini_groups
                request.session['ordini_da_pianificare_groups'] = ordini_da_pianificare_groups
                request.session['avanzamento_ordini'] = avanzamento_ordini
                request.session['avanzamento_ordini_preferences'] = avanzamento_ordini_preferences
                request.session['ordini_da_pianificare'] = ordini_da_pianificare
                request.session['ordini_da_pianificare_preferences'] = ordini_da_pianificare_preferences

            except Exception as e:
                import traceback
                traceback.print_exc()

        elif action == "update_ord_single":
            try:
                numero_ordine = request.POST.get('ordine')
                riga = int(request.POST.get('riga'))
                nuovo_operatore_nome = request.POST.get('operatore')
                nuovo_stato_nome = request.POST.get('stato')
                
                stato_obj = Stati_Ordini.objects.filter(stato=nuovo_stato_nome).first()
                operatore_obj = Utenti.objects.filter(nome=nuovo_operatore_nome).first()
                
                ordine_db = Avanzamento_Ordini.objects.filter(ordine=numero_ordine, n_riga=riga).first()

                adv_idx   = {(o['sede'], o['ordine'], o['n_riga']): o for o in avanzamento_ordini}
                pian_idx  = {(o['sede'], o['ordine'], o['n_riga']): o for o in ordini_da_pianificare}

                k = (ordine_db.sede, ordine_db.ordine, ordine_db.n_riga)

                if ordine_db.stato_ord.stato == "Da pianificare" and stato_obj.stato != "Da pianificare":
                    pian_idx.pop(k, None)
                elif ordine_db.stato_ord.stato != "Da pianificare" and stato_obj.stato == "Da pianificare":
                    pian_idx[k] = adv_idx[k] 

                ordini_da_pianificare = list(pian_idx.values())

                # Aggiorna il DB
                Avanzamento_Ordini.objects.filter(id=ordine_db.id) \
                    .update(operatore=operatore_obj, stato_ord=stato_obj)


                for ordine in avanzamento_ordini:
                    if ordine['ordine'] == numero_ordine and ordine['n_riga'] == riga:
                        ordine['operatore'] = operatore_obj.username if operatore_obj is not None else None
                        ordine['des_operatore'] = operatore_obj.nome if operatore_obj is not None else None
                        ordine['id_stato_ord'] = stato_obj.id if stato_obj is not None else None
                        ordine['des_stato_ord'] = stato_obj.stato if stato_obj is not None else None

                # Salva in sessione
                avanzamento_ordini_preferences = get_ordini_preferences(avanzamento_ordini)
                ordini_da_pianificare_preferences = get_ordini_preferences(ordini_da_pianificare)        
                avanzamento_ordini_groups = group(avanzamento_ordini)
                ordini_da_pianificare_groups = group(ordini_da_pianificare)      

                request.session['avanzamento_ordini_groups'] = avanzamento_ordini_groups
                request.session['ordini_da_pianificare_groups'] = ordini_da_pianificare_groups
                request.session['avanzamento_ordini'] = avanzamento_ordini
                request.session['avanzamento_ordini_preferences'] = avanzamento_ordini_preferences
                request.session['ordini_da_pianificare'] = ordini_da_pianificare
                request.session['ordini_da_pianificare_preferences'] = ordini_da_pianificare_preferences
            except Exception as e:
                import traceback
                traceback.print_exc()
        elif action == "update_note":
            try:
                numero_ordine = request.POST.get('ordine')
                nota = request.POST.get('nota')
                ordini_selezionati = Avanzamento_Ordini.objects.filter(ordine=numero_ordine)
                ordini_selezionati.update(note_prod=nota)
                idx_ordine_da_pianificare = False
                for ordine in avanzamento_ordini:
                    if ordine['ordine'] == numero_ordine:
                        ordine['note_prod'] = nota
                        if ordine['des_stato_ord']== "Da pianificare":
                            idx_ordine_da_pianificare = True
                if idx_ordine_da_pianificare:
                    for ordine in ordini_da_pianificare:
                        if ordine['ordine'] == numero_ordine:
                            ordine['note_prod'] = nota

                    ordini_da_pianificare_groups = group(ordini_da_pianificare)
                avanzamento_ordini_groups = group(avanzamento_ordini)
                request.session['avanzamento_ordini_groups'] = avanzamento_ordini_groups
                request.session['avanzamento_ordini'] = avanzamento_ordini
                request.session['ordini_da_pianificare'] = ordini_da_pianificare
                request.session['avanzamento_ordini_groups'] = avanzamento_ordini_groups
            except Exception as e:
                import traceback
                traceback.print_exc()
        elif action == "update_note_single":
            try:
                numero_ordine = request.POST.get('ordine')
                riga = int(request.POST.get('riga'))
                nota = request.POST.get('nota')
                ordini_selezionati = Avanzamento_Ordini.objects.filter(ordine=numero_ordine, n_riga=riga).first()
                idx_ordine_da_pianificare = False
                if ordini_selezionati:
                    ordini_selezionati.note_prod = nota
                    ordini_selezionati.save()
                    if ordini_selezionati.stato_ord.stato == "Da pianificare":
                        idx_ordine_da_pianificare = True
                for ordine in avanzamento_ordini:
                    if ordine['ordine'] == numero_ordine and ordine['n_riga'] == riga:
                        ordine['note_prod'] = nota
                if idx_ordine_da_pianificare:
                    for ordine in ordini_da_pianificare:
                        if ordine['ordine'] == numero_ordine and ordine['n_riga'] == riga:
                            ordine['note_prod'] = nota
                    ordini_da_pianificare_groups = group(ordini_da_pianificare)
                avanzamento_ordini_groups = group(avanzamento_ordini)
                request.session['avanzamento_ordini_groups'] = avanzamento_ordini_groups
                request.session['avanzamento_ordini'] = avanzamento_ordini
                request.session['ordini_da_pianificare'] = ordini_da_pianificare
                request.session['avanzamento_ordini_groups'] = avanzamento_ordini_groups
            except Exception as e:
                import traceback
                traceback.print_exc()

    avanzamento_ordini_render = riformatta_date(copy.deepcopy(avanzamento_ordini))
    avanzamento_ordini_groups_render = riformatta_date_groups(copy.deepcopy(avanzamento_ordini_groups))
    today = date.today()

    if ordine_filtro or cliente_filtro or stato_filtro or operatore_filtro or articolo_filtro or old_code_filtro:
        avanzamento_ordini_render = [
            o for o in avanzamento_ordini_render
            if (not ordine_filtro or ordine_filtro.lower() in (o.get('ordine') or '').lower()) and
            (not cliente_filtro or cliente_filtro.lower() in (o.get('des_cliente') or '').lower()) and
            (not stato_filtro or stato_filtro.lower() in (o.get('des_stato_ord') or '').lower()) and
            (not operatore_filtro or operatore_filtro.lower() in (o.get('des_operatore') or '').lower()) and 
            (not articolo_filtro or articolo_filtro.lower() in (o.get('articolo') or '').lower()) and
            (not old_code_filtro or old_code_filtro.lower() in (o.get('old_code') or '').lower())
        ]


        avanzamento_ordini_groups_render = group(avanzamento_ordini_render)
    context = {
        'today': today,
        'modalita': modalita,
        "filtro": {
            "ordine": ordine_filtro,
            "cliente": cliente_filtro,
            "stato": stato_filtro,
            "operatore": operatore_filtro,
            "articolo": articolo_filtro,
            "old_code": old_code_filtro,
        },
        'ruolo_utente': ruolo_utente,
        'stati_ordini': stati_ordini,
        'operatori': operatori,
        'avanzamento_ordini': avanzamento_ordini_render,
        'avanzamento_ordini_groups': avanzamento_ordini_groups_render,
        'avanzamento_ordini_preferences': avanzamento_ordini_preferences,
        'nome_utente': nome_utente,
    }
    
    return render(request, 'produzione/avanzamento_ordini.html', context)

@login_required(login_url='login')
def ordini_da_pianificare(request):
    modalita = request.GET.get('modalita', 'standard')
    ordine_filtro   = request.GET.get("ordine_filtro", "")
    cliente_filtro   = request.GET.get("cliente_filtro", "")
    stato_filtro     = request.GET.get("stato_filtro", "")
    operatore_filtro = request.GET.get("operatore_filtro", "")
    articolo_filtro = request.GET.get("articolo_filtro", "")
    old_code_filtro = request.GET.get("old_code_filtro", "")
    avanzamento_ordini = request.session.get('avanzamento_ordini')
    ordini_da_pianificare = request.session.get('ordini_da_pianificare')
    avanzamento_ordini_preferences = request.session.get('avanzamento_ordini_preferences')
    ordini_da_pianificare_preferences = request.session.get('ordini_da_pianificare_preferences')
    avanzamento_ordini_groups = request.session.get('avanzamento_ordini_groups')
    ordini_da_pianificare_groups = request.session.get('ordini_da_pianificare_groups')
    ruolo_utente = request.session.get('ruolo_utente')
    nome_utente = request.session['nome_utente']
    
    stati_ordini = list(
    Stati_Ordini.objects.values_list('stato', flat=True).distinct().order_by('stato')
        )

    operatori = list(
        Utenti.objects.filter(is_operatore=True).values_list('nome', flat=True).distinct().order_by('nome')
        )
    
    if request.method == 'POST':
        modalita = request.GET.get('modalita', 'standard')
        ordine_filtro   = request.GET.get("ordine_filtro", "")
        cliente_filtro   = request.GET.get("cliente_filtro", "")
        stato_filtro     = request.GET.get("stato_filtro", "")
        operatore_filtro = request.GET.get("operatore_filtro", "")
        articolo_filtro = request.GET.get("articolo_filtro", "")
        old_code_filtro = request.GET.get("old_code_filtro", "")
        action = request.POST.get('form_type')
        if action == "general_update":
            if ruolo_utente in ["Amministratore", "Pianificazione"]:
                aggiorna_dati(request)
            avanzamento_ordini, ordini_da_pianificare, storico_ordini = select_ordini(request, ruolo_utente)
            avanzamento_ordini_preferences = get_ordini_preferences(avanzamento_ordini)
            ordini_da_pianificare_preferences = get_ordini_preferences(ordini_da_pianificare)
            storico_ordini_preferences = get_ordini_preferences(storico_ordini)
            avanzamento_ordini_groups = group(avanzamento_ordini)
            ordini_da_pianificare_groups = group(ordini_da_pianificare)
            storico_ordini_groups = group(storico_ordini)        

            request.session['avanzamento_ordini'] = avanzamento_ordini 
            request.session['ordini_da_pianificare'] = ordini_da_pianificare
            request.session['storico_ordini'] = storico_ordini
            request.session['avanzamento_ordini_preferences'] = avanzamento_ordini_preferences
            request.session['ordini_da_pianificare_preferences'] = ordini_da_pianificare_preferences
            request.session['storico_ordini_preferences'] = storico_ordini_preferences
            request.session['avanzamento_ordini_groups'] = avanzamento_ordini_groups
            request.session['ordini_da_pianificare_groups'] = ordini_da_pianificare_groups
            request.session['storico_ordini_groups'] = storico_ordini_groups
        
        elif action == "update_ord_list":
            try:
                numero_ordine = request.POST.get('ordine')
                nuovo_operatore_nome = request.POST.get('operatore')
                nuovo_stato_nome = request.POST.get('stato')
                
                stato_obj = Stati_Ordini.objects.filter(stato=nuovo_stato_nome).first()
                operatore_obj = Utenti.objects.filter(nome=nuovo_operatore_nome).first()

                ordini_selezionati = Avanzamento_Ordini.objects.filter(ordine=numero_ordine, )

                pian_idx  = {(o['sede'], o['ordine'], o['n_riga']): o for o in ordini_da_pianificare}

                if stato_obj.stato != "Da pianificare":
                    for row in ordini_selezionati:
                        k = (row.sede, row.ordine, row.n_riga)
                        pian_idx.pop(k, None)

                ordini_da_pianificare = list(pian_idx.values())

                # Aggiorna il DB
                ordini_selezionati.update(
                    operatore=operatore_obj,
                    stato_ord=stato_obj
                )

                # Aggiorna la sessione di avanzamento_ordini
                for ordine in avanzamento_ordini:
                    if ordine['ordine'] == numero_ordine:
                        ordine['operatore'] = operatore_obj.username if operatore_obj else None
                        ordine['des_operatore'] = operatore_obj.nome if operatore_obj else None
                        ordine['id_stato_ord'] = stato_obj.id if stato_obj else None
                        ordine['des_stato_ord'] = stato_obj.stato if stato_obj else None

                # Salva in sessione
                avanzamento_ordini_preferences = get_ordini_preferences(avanzamento_ordini)
                ordini_da_pianificare_preferences = get_ordini_preferences(ordini_da_pianificare)
                avanzamento_ordini_groups = group(avanzamento_ordini)
                ordini_da_pianificare_groups = group(ordini_da_pianificare)    

                request.session['avanzamento_ordini'] = avanzamento_ordini 
                request.session['ordini_da_pianificare'] = ordini_da_pianificare
                request.session['avanzamento_ordini_preferences'] = avanzamento_ordini_preferences
                request.session['ordini_da_pianificare_preferences'] = ordini_da_pianificare_preferences
                request.session['avanzamento_ordini_groups'] = avanzamento_ordini_groups
                request.session['ordini_da_pianificare_groups'] = ordini_da_pianificare_groups

            except Exception as e:
                import traceback
                traceback.print_exc()

        elif action == "update_ord_single":
            try:
                numero_ordine = request.POST.get('ordine')
                riga = int(request.POST.get('riga'))
                nuovo_operatore_nome = request.POST.get('operatore')
                nuovo_stato_nome = request.POST.get('stato')
                
                stato_obj = Stati_Ordini.objects.filter(stato=nuovo_stato_nome).first()
                operatore_obj = Utenti.objects.filter(nome=nuovo_operatore_nome).first()
                
                ordine_db = Avanzamento_Ordini.objects.filter(ordine=numero_ordine, n_riga=riga).first()

                pian_idx  = {(o['sede'], o['ordine'], o['n_riga']): o for o in ordini_da_pianificare}

                k = (ordine_db.sede, ordine_db.ordine, ordine_db.n_riga)

                if stato_obj.stato != "Da pianificare":
                    pian_idx.pop(k, None)

                ordini_da_pianificare = list(pian_idx.values())

                # Aggiorna il DB
                Avanzamento_Ordini.objects.filter(id=ordine_db.id) \
                    .update(operatore=operatore_obj, stato_ord=stato_obj)

                for ordine in avanzamento_ordini:
                    if ordine['ordine'] == numero_ordine and ordine['n_riga'] == riga:
                        ordine['operatore'] = operatore_obj.username if operatore_obj is not None else None
                        ordine['des_operatore'] = operatore_obj.nome if operatore_obj is not None else None
                        ordine['id_stato_ord'] = stato_obj.id if stato_obj is not None else None
                        ordine['des_stato_ord'] = stato_obj.stato if stato_obj is not None else None

                # Salva in sessione
                avanzamento_ordini_preferences = get_ordini_preferences(avanzamento_ordini)
                ordini_da_pianificare_preferences = get_ordini_preferences(ordini_da_pianificare)
                avanzamento_ordini_groups = group(avanzamento_ordini)
                ordini_da_pianificare_groups = group(ordini_da_pianificare)    

                request.session['avanzamento_ordini'] = avanzamento_ordini 
                request.session['ordini_da_pianificare'] = ordini_da_pianificare
                request.session['avanzamento_ordini_preferences'] = avanzamento_ordini_preferences
                request.session['ordini_da_pianificare_preferences'] = ordini_da_pianificare_preferences
                request.session['avanzamento_ordini_groups'] = avanzamento_ordini_groups
                request.session['ordini_da_pianificare_groups'] = ordini_da_pianificare_groups
            except Exception as e:
                import traceback
                traceback.print_exc()
        elif action == "update_note":
            try:
                numero_ordine = request.POST.get('ordine')
                nota = request.POST.get('nota')
                ordini_selezionati = Avanzamento_Ordini.objects.filter(ordine=numero_ordine)
                ordini_selezionati.update(note_prod=nota)
                for ordine in avanzamento_ordini:
                    if ordine['ordine'] == numero_ordine:
                        ordine['note_prod'] = nota

                for ordine in ordini_da_pianificare:
                    if ordine['ordine'] == numero_ordine:
                        ordine['note_prod'] = nota

                ordini_da_pianificare_groups = group(ordini_da_pianificare)
                avanzamento_ordini_groups = group(avanzamento_ordini)
                request.session['avanzamento_ordini_groups'] = avanzamento_ordini_groups
                request.session['avanzamento_ordini'] = avanzamento_ordini
                request.session['ordini_da_pianificare'] = ordini_da_pianificare
                request.session['avanzamento_ordini_groups'] = avanzamento_ordini_groups
            except Exception as e:
                import traceback
                traceback.print_exc()
        elif action == "update_note_single":
            try:
                numero_ordine = request.POST.get('ordine')
                riga = int(request.POST.get('riga'))
                nota = request.POST.get('nota')
                ordini_selezionati = Avanzamento_Ordini.objects.filter(ordine=numero_ordine, n_riga=riga).first()
                if ordini_selezionati:
                    ordini_selezionati.note_prod = nota
                    ordini_selezionati.save()

                for ordine in avanzamento_ordini:
                    if ordine['ordine'] == numero_ordine and ordine['n_riga'] == riga:
                        ordine['note_prod'] = nota
                for ordine in ordini_da_pianificare:
                    if ordine['ordine'] == numero_ordine and ordine['n_riga'] == riga:
                        ordine['note_prod'] = nota
                ordini_da_pianificare_groups = group(ordini_da_pianificare)
                avanzamento_ordini_groups = group(avanzamento_ordini)
                request.session['avanzamento_ordini_groups'] = avanzamento_ordini_groups
                request.session['avanzamento_ordini'] = avanzamento_ordini
                request.session['ordini_da_pianificare'] = ordini_da_pianificare
                request.session['avanzamento_ordini_groups'] = avanzamento_ordini_groups
            except Exception as e:
                import traceback
                traceback.print_exc()

    ordini_da_pianificare_render = riformatta_date(copy.deepcopy(ordini_da_pianificare))
    ordini_da_pianificare_groups_render = riformatta_date_groups(copy.deepcopy(ordini_da_pianificare_groups))
    today = date.today()

    if ordine_filtro or cliente_filtro or stato_filtro or operatore_filtro or articolo_filtro or old_code_filtro:
        ordini_da_pianificare_render = [
            o for o in ordini_da_pianificare_render
            if (not ordine_filtro or ordine_filtro.lower() in (o.get('ordine') or '').lower()) and
            (not cliente_filtro or cliente_filtro.lower() in (o.get('des_cliente') or '').lower()) and
            (not stato_filtro or stato_filtro.lower() in (o.get('des_stato_ord') or '').lower()) and
            (not operatore_filtro or operatore_filtro.lower() in (o.get('des_operatore') or '').lower()) and 
            (not articolo_filtro or articolo_filtro.lower() in (o.get('articolo') or '').lower()) and
            (not old_code_filtro or old_code_filtro.lower() in (o.get('old_code') or '').lower())
        ]

        ordini_da_pianificare_groups_render = group(ordini_da_pianificare_render)

    context = {
        'today': today,
        'modalita': modalita,
        "filtro": {
            "ordine": ordine_filtro,
            "cliente": cliente_filtro,
            "stato": stato_filtro,
            "operatore": operatore_filtro,
            "articolo": articolo_filtro,
            "old_code": old_code_filtro,
        },
        'ruolo_utente': ruolo_utente,
        'stati_ordini': stati_ordini,
        'operatori': operatori,
        'avanzamento_ordini': ordini_da_pianificare_render,
        'avanzamento_ordini_groups': ordini_da_pianificare_groups_render,
        'avanzamento_ordini_preferences': ordini_da_pianificare_preferences,
        'nome_utente': nome_utente
    }
    
    return render(request, 'produzione/ordini_da_pianificare.html', context)

@login_required(login_url='login')
def storico_ordini(request):
    modalita = request.GET.get('modalita', 'standard')
    ordine_filtro   = request.GET.get("ordine_filtro", "")
    cliente_filtro   = request.GET.get("cliente_filtro", "")
    stato_filtro     = request.GET.get("stato_filtro", "")
    operatore_filtro = request.GET.get("operatore_filtro", "")
    articolo_filtro = request.GET.get("articolo_filtro", "")
    old_code_filtro = request.GET.get("old_code_filtro", "")
    storico_ordini = request.session.get('storico_ordini')
    storico_ordini_groups = request.session.get('storico_ordini_groups')
    storico_ordini_preferences = request.session.get('storico_ordini_preferences')
    ruolo_utente = request.session.get('ruolo_utente')
    nome_utente = request.session['nome_utente']
    if request.method == 'POST':
        action = request.POST.get('form_type')
        if action == "update_note":
            try:
                numero_ordine = request.POST.get('ordine')
                nota = request.POST.get('nota')
                ordini_selezionati = Avanzamento_Ordini.objects.filter(ordine=numero_ordine)
                ordini_selezionati.update(note_prod=nota)
                for ordine in storico_ordini:
                    if ordine['ordine'] == numero_ordine:
                        ordine['note_prod'] = nota

                storico_ordini_groups = group(storico_ordini)
                request.session['storico_ordini_groups'] = storico_ordini_groups
                request.session['storico_ordini'] = storico_ordini
            except Exception as e:
                import traceback
                traceback.print_exc()
        elif action == "update_note_single":
            try:
                numero_ordine = request.POST.get('ordine')
                riga = int(request.POST.get('riga'))
                nota = request.POST.get('nota')
                ordini_selezionati = Avanzamento_Ordini.objects.filter(ordine=numero_ordine, n_riga=riga).first()
                if ordini_selezionati:
                    ordini_selezionati.note_prod = nota
                    ordini_selezionati.save()

                for ordine in storico_ordini:
                    if ordine['ordine'] == numero_ordine and ordine['n_riga'] == riga:
                        ordine['note_prod'] = nota

                storico_ordini_groups = group(storico_ordini)
                request.session['storico_ordini_groups'] = storico_ordini_groups
                request.session['storico_ordini'] = storico_ordini
            except Exception as e:
                import traceback
                traceback.print_exc()
    storico_ordini_groups_render = riformatta_date_groups(copy.deepcopy(storico_ordini_groups))
    storico_ordini_render = riformatta_date(copy.deepcopy(storico_ordini))
    today = date.today()

    if ordine_filtro or cliente_filtro or stato_filtro or operatore_filtro or articolo_filtro or old_code_filtro:
        storico_ordini_render = [
            o for o in storico_ordini_render
            if (not ordine_filtro or ordine_filtro.lower() in (o.get('ordine') or '').lower()) and
            (not cliente_filtro or cliente_filtro.lower() in (o.get('des_cliente') or '').lower()) and
            (not stato_filtro or stato_filtro.lower() in (o.get('des_stato_ord') or '').lower()) and
            (not operatore_filtro or operatore_filtro.lower() in (o.get('des_operatore') or '').lower()) and 
            (not articolo_filtro or articolo_filtro.lower() in (o.get('articolo') or '').lower()) and
            (not old_code_filtro or old_code_filtro.lower() in (o.get('old_code') or '').lower())
        ]
        storico_ordini_groups_render = group(storico_ordini_render)

    context = {
        'today': today,
        'modalita': modalita,
        "filtro": {
            "ordine": ordine_filtro,
            "cliente": cliente_filtro,
            "stato": stato_filtro,
            "operatore": operatore_filtro,
            "articolo": articolo_filtro,
            "old_code": old_code_filtro,
        },
        'ruolo_utente': ruolo_utente,
        'avanzamento_ordini': storico_ordini_render,
        'avanzamento_ordini_groups': storico_ordini_groups_render,
        'avanzamento_ordini_preferences': storico_ordini_preferences,
        'nome_utente': nome_utente
    }
    
    return render(request, 'produzione/storico_ordini.html', context)

@login_required(login_url='login')
def tabelle(request):
    ruolo_utente = request.session.get('ruolo_utente')
    tipo = request.GET.get('tipo', '')
    nome_utente = request.session['nome_utente']

    if request.method == "POST" and tipo == "utenti":
        action = request.POST.get("action")
        user_id = request.POST.get("user_id")
        errore = False

        try:
            utente = Utenti.objects.get(id=user_id)
        except Utenti.DoesNotExist:
            utente = None

        if action == "update" and utente:
            new_user = request.POST.get("username")
            new_nome = request.POST.get("nome")
            new_ruolo_id = request.POST.get("ruolo")

            if utente.username != new_user and Utenti.objects.filter(username=new_user).exists():
                messages.error(request, "Username già esistente. Scegline uno diverso.")
                errore = True
            else:
                utente.username = new_user

            if utente.nome != new_nome and Utenti.objects.filter(nome=new_nome).exists():
                messages.error(request, "Nome già esistente. Scegline uno diverso.")
                errore = True
            else:
                utente.nome = new_nome
            
            if new_ruolo_id:
                new_ruolo = Profili.objects.get(id=new_ruolo_id)
            else:
                new_ruolo = None
            utente.ruolo = new_ruolo

            is_op = request.POST.get("is_operatore")
            utente.is_operatore = {"True": True, "False": False}.get(is_op, None)

            nuova_password = request.POST.get("password")
            if nuova_password:
                utente.set_password(nuova_password)


            if not errore:
                utente.save()

        elif action == "create":
            username = request.POST.get("utente_nome")
            nome = request.POST.get("nome")
            is_op = request.POST.get("is_operatore")
            password = request.POST.get("pass_visibile")
            new_ruolo_id = request.POST.get("ruolo")

            if Utenti.objects.filter(username=username).exists():
                messages.error(request, "Username già esistente.")
                errore = True
            elif Utenti.objects.filter(nome=nome).exists():
                messages.error(request, "Nome già esistente.")
                errore = True
            elif not username or not password:
                messages.error(request, "Username e password sono obbligatori.")
                errore = True
            else:
                nuovo_utente = Utenti(
                    username=username,
                    nome=nome,
                    is_operatore={"True": True, "False": False}.get(is_op, None),
                    ruolo=Profili.objects.get(id=new_ruolo_id) if new_ruolo_id else None
                )
                nuovo_utente.set_password(password)
                nuovo_utente.save()

        elif action == "delete" and utente:
            utente.delete()

        # Se tutto è andato bene, redirect e torna alla sezione utenti
        return redirect(request.path + "?tipo=utenti")

    if request.method == "POST" and tipo == "profili":
        action = request.POST.get("action")
        profilo_id = request.POST.get("profilo_id")

        try:
            profilo = Profili.objects.get(id=profilo_id)
        except Profili.DoesNotExist:
            profilo = None

        if action == "update" and profilo:
            old_id = request.POST.get("profilo_id")
            new_id = request.POST.get("id_profilo")
            ruolo = request.POST.get("ruolo")

            if old_id != new_id and ruolo == profilo.ruolo:
                if not Profili.objects.filter(id=new_id).exists():
                    profilo.delete()
                    nuovo_profilo = Profili(id=new_id, ruolo=ruolo)
                    nuovo_profilo.save()
                else:
                    messages.error(request, "Codice già esistente. Scegline uno diverso.")
            elif profilo.ruolo != ruolo and old_id == new_id:
                if Profili.objects.filter(ruolo=ruolo).exists():
                    messages.error(request, "Ruolo già esistente. Scegline uno diverso.")
                else:
                    profilo.ruolo = ruolo
                    profilo.save()
            elif profilo.ruolo != ruolo and old_id != new_id:
                if Profili.objects.filter(ruolo=ruolo).exists() or Profili.objects.filter(id=new_id).exists():
                    messages.error(request, "Codice o Ruolo già esistente. Scegline uno diverso.")
                else:
                    nuovo_profilo = Profili(id=new_id, ruolo=ruolo)
                    nuovo_profilo.save()


        elif action == "create":
            id_profilo = request.POST.get("id_profilo")
            ruolo = request.POST.get("ruolo")
            
            if not Profili.objects.filter(id=id_profilo).exists() and not Profili.objects.filter(ruolo=ruolo).exists():
                if id_profilo and ruolo:
                    nuovo_profilo = Profili(
                        id=id_profilo,
                        ruolo=ruolo
                    )
                    nuovo_profilo.save()
            else:
                messages.error(request, "Codice o Ruolo già esistente. Scegline uno diverso.")

        elif action == "delete" and profilo:
            profilo.delete()

        return redirect(request.path + f"?tipo=profili")

    if request.method == "POST" and tipo == "stati_ordini":
        action = request.POST.get("action")
        stato_id = request.POST.get("stato_id")

        try:
            stato = Stati_Ordini.objects.get(id=stato_id)
        except Stati_Ordini.DoesNotExist:
            stato = None

        if action == "update" and stato:
            old_id = request.POST.get("stato_id")
            new_id = request.POST.get("id_stato")
            new_stato = request.POST.get("stato")

            if old_id != new_id and new_stato == stato.stato:
                if not Stati_Ordini.objects.filter(id=new_id).exists():
                    stato.delete()
                    nuovo_stato = Stati_Ordini(id=new_id, stato=new_stato)
                    nuovo_stato.save()
                else:
                    messages.error(request, "Codice già esistente. Scegline uno diverso.")
            elif stato.stato != new_stato and old_id == new_id:
                if Stati_Ordini.objects.filter(stato=new_stato).exists():
                    messages.error(request, "Stato già esistente. Scegline uno diverso.")
                else:
                    stato.stato = new_stato
                    stato.save()
            elif stato.stato != new_stato and old_id != new_id:
                if Stati_Ordini.objects.filter(stato=new_stato).exists() or Stati_Ordini.objects.filter(id=new_id).exists():
                    messages.error(request, "Codice o Stato già esistente. Scegline uno diverso.")
                else:
                    nuovo_stato = Stati_Ordini(id=new_id, stato=new_stato)
                    nuovo_stato.save()

        elif action == "create":
            id_stato = request.POST.get("id_stato")
            stato = request.POST.get("stato")
            
            if not Stati_Ordini.objects.filter(id=id_stato).exists() and not Stati_Ordini.objects.filter(stato=stato).exists():
                if id_stato and stato:
                    nuovo_stato = Stati_Ordini(
                        id=id_stato,
                        stato=stato
                    )
                    nuovo_stato.save()
            else:
                messages.error(request, "Codice o Stato già esistente. Scegline uno diverso.")

        elif action == "delete" and stato:
            stato.delete()

        return redirect(request.path + f"?tipo=stati_ordini")

    if request.method == "POST" and tipo == "legami_utenti-profili":

        utente_id = request.POST.get("utente_id")
        ruolo_id = request.POST.get("ruolo")

        try:
            utente = Utenti.objects.get(id=utente_id)
        except Utenti.DoesNotExist:
            utente = None

        if utente:
            if ruolo_id:
                profilo = Profili.objects.get(id=ruolo_id)
                utente.ruolo = profilo
            else:
                utente.ruolo = None
            utente.save()

        return redirect(request.path + f"?tipo=legami_utenti-profili")

    if request.method == "POST" and tipo == "legami_profili-stati_ordini":
        action = request.POST.get("action")
        id_profilo_stato = request.POST.get("id_profilo_stato")

        try:
            profilo_stato = Profili_Stati.objects.get(id=id_profilo_stato)
        except Profili_Stati.DoesNotExist:
            profilo_stato = None
        
        if action == 'delete' and profilo_stato:
            profilo_stato.delete()

        elif action == 'create':
            id_ruolo = request.POST.get("ruolo")
            id_stato = request.POST.get("stato")
            tipo_uso = request.POST.get("tipo_uso")
            ruolo = Profili.objects.get(id=id_ruolo)
            stato = Stati_Ordini.objects.get(id=id_stato)
            if Profili_Stati.objects.filter(ruolo=ruolo, stato_ord=stato, tipo_uso=tipo_uso).exists():
                messages.error(request, "Riga già presente.")
            else:
                nuovo_profilo_stato = Profili_Stati(ruolo=ruolo, stato_ord=stato, tipo_uso=tipo_uso)
                nuovo_profilo_stato.save()

        return redirect(request.path + f"?tipo=legami_profili-stati_ordini")
    
    utenti = Utenti.objects.all()
    profili = Profili.objects.all()
    stati = Stati_Ordini.objects.all()
    profili_stati = Profili_Stati.objects.all()

    context = {
        'ruolo_utente': ruolo_utente,
        'tipo': tipo,
        'utenti': utenti,
        'profili': profili,
        'stati': stati,
        'profili_stati': profili_stati,
        'nome_utente': nome_utente
    }
    
    return render(request, 'produzione/tabelle.html', context)

def group(ordini):
    raggruppamenti = []
    group_map = defaultdict(list)

    for item in ordini:
        key = (item['des_cliente'], item['ordine'], item['sede'])
        group_map[key].append(item)

    for (cliente, ordine, sede), dati in group_map.items():
        percentuali_stato={}
        for dato in dati:
            if dato['des_stato_ord'] in percentuali_stato.keys():
                percentuali_stato [dato['des_stato_ord']] += 1
            else:
                percentuali_stato [dato['des_stato_ord']] = 1
        somma = sum(percentuali_stato.values())
        for k,v in percentuali_stato.items():
            percentuali_stato[k] = int(round(v / somma * 100,0))
        
        raggruppamenti.append({
            'cliente': cliente,
            'ordine': ordine,
            'sede': sede,
            'percentuali_stato': percentuali_stato,
            'data_cons': dati[0]['data_cons'],
            'dati': dati,
        })
        
    raggruppamenti.sort(key=lambda x: (x['cliente']))
    return raggruppamenti

def get_ordini_preferences(avanzamento_ordini):
    
    # Inizializza set vuoti per raccogliere valori unici
    ordini_unici = set()
    clienti_unici = set()
    stati_unici = set()
    operatori_unici = set()
    articoli_unici = set()
    old_codes_unici = set()

    # Un solo ciclo per popolare tutti i set
    for item in avanzamento_ordini:
        if item['ordine']:
            ordini_unici.add(item['ordine'])
        if item['des_cliente']:
            clienti_unici.add(item['des_cliente'])
        if item['des_stato_ord']:
            stati_unici.add(item['des_stato_ord'])
        if item['des_operatore']:
            operatori_unici.add(item['des_operatore'])
        if item['articolo']:
            articoli_unici.add(item['articolo'])
        if item['old_code']:
            old_codes_unici.add(item['old_code'])

    # (Opzionale) Ordina i set convertendoli in liste
    ordini_unici = list(ordini_unici)
    clienti_unici = list(clienti_unici)
    stati_unici = list(stati_unici)
    operatori_unici = list(operatori_unici)
    articoli_unici = list(articoli_unici)
    old_codes_unici = list(old_codes_unici)

    return {
        'ordini_unici': ordini_unici,
        'clienti_unici': clienti_unici,
        'stati_unici': stati_unici,
        'operatori_unici': operatori_unici,
        'articoli_unici': articoli_unici,
        'old_codes_unici': old_codes_unici,
    }

def aggiorna_dati(request):
    try:
        with transaction.atomic():
            # 0.Accedi a sage
            connection = bsdb04_connection()

            # 1.Aggiorna Avanzamento Ordini
            with open(constant.C_QUERY_AVANZAMENTO_ORDINI, 'r', encoding='utf-8') as file:
                query_avanzamento_ordini = file.read()

            with connection.cursor() as cursor:
                cursor.execute(query_avanzamento_ordini)
                response_avanzamento_ordini = cursor.fetchall()
            
                # Ottieni chiavi già esistenti nel DB
                esistenti = set(
                    Avanzamento_Ordini.objects
                    .values_list('sede', 'ordine', 'n_riga')
                )

                # Filtra solo quelli nuovi
                ordini_nuovi = [
                    Avanzamento_Ordini(
                        sede=row[0],
                        ordine=row[1],
                        n_riga=row[2],
                        stato_ord=Stati_Ordini.objects.get(id=row[3]),
                        note=row[4]
                    )
                    for row in response_avanzamento_ordini
                    if (row[0], row[1], row[2]) not in esistenti
                ]

            Avanzamento_Ordini.objects.bulk_create(ordini_nuovi, batch_size=1000)

            # 2.Cancella le note presenti
            Note_Ordini.objects.all().delete()

            # 3.Verifico la presenza di nuove note per ordini già presenti
            with open(constant.C_QUERY_X_NOTE, 'r', encoding='utf-8') as file:
                query_x_note = file.read()

            with connection.cursor() as cursor:
                cursor.execute(query_x_note)
                response_x_note = cursor.fetchall()

            # Ordini senza note
            ordini = set(Avanzamento_Ordini.objects
                        .filter(Q(note__isnull=True) | Q(note='') | Q(note=' '))
                        .values_list('sede', 'ordine'))

            for cpy, sohn, sohtex1 in response_x_note:
                if (cpy, sohn) in ordini:
                    Note_Ordini.objects.create(sede=cpy, ordine=sohn, note=sohtex1)
                    Avanzamento_Ordini.objects.filter(sede=cpy, ordine=sohn).update(note=sohtex1)

            # 4. Recupera gli ordini con note da aggiornare
            ordini = Avanzamento_Ordini.objects.filter(fl_note_ord="S")

            for ordine in ordini:
                cpy = ordine.sede
                sohnum = ordine.ordine
                sohtex = ordine.note

                # Cerca la nota esistente
                note = Note.objects.filter(ordine=sohnum).first()
                if note and sohtex:
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT TEXTE_0 FROM PROD.TEXCLOB WHERE CODE_0 = ?", [sohtex])
                        row = cursor.fetchone()
                    
                    if row:
                        nuovo_testo = row[0]

                        if note.testo.strip() != nuovo_testo.strip():
                            note.testo = nuovo_testo
                            note.fl_upd = "S"
                            note.save()


            # 6. Accoda eventuali nuove note (non aggiornate)
            ordini = Avanzamento_Ordini.objects.exclude(note__isnull=True).exclude(note='').exclude(note=' ') \
                    .values_list('sede', 'ordine', 'note')

            mappa = defaultdict(list)
            for sede, ordine, note in ordini:
                mappa[note].append((sede, ordine))
            codici = list(mappa.keys())

            if codici:
                placeholders = ','.join(['?'] * len(codici))  # ODBC usa '?' invece di %s

                query = f"""
                    SELECT CODE_0, TEXTE_0
                    FROM PROD.TEXCLOB
                    WHERE CODE_0 IN ({placeholders})
                    AND TEXTE_0 LIKE '{{\\rtf1%%'
                """

                with connection.cursor() as cursor:
                    cursor.execute(query, codici)
                    rows = cursor.fetchall()

                nuove_note = []
                for code, testo in rows:
                    for sede, ordine in mappa.get(code, []):
                        nuove_note.append(Note(sede=sede, ordine=ordine, testo=testo))

                Note.objects.bulk_create(nuove_note)

            # 7. Aggiorna flag "note elaborate"
            note_keys = set(Note.objects.values_list('sede', 'ordine'))

            q = Q()
            for sede, ordine in note_keys:
                q |= Q(sede=sede, ordine=ordine)
            if q:
                Avanzamento_Ordini.objects.filter(q).update(fl_note_ord="S")

    except Exception as e:
        messages.error(request, f"Errore aggiornamento dati: {str(e)}")

def select_ordini(request, ruolo_utente):
    try:
        with transaction.atomic():            # 0.Accedi a sage
            connection = bsdb04_connection()

            # 1.Aggiorna Ordini
            with open(constant.C_QUERY_ORDINI_APERTI, 'r', encoding='utf-8') as file:
                query_ordini_aperti = file.read()

            with open(constant.C_QUERY_ORDINI_CHIUSI, 'r', encoding='utf-8') as file:
                query_ordini_chiusi = file.read()

            with connection.cursor() as cursor:
                # Esegui la prima query
                cursor.execute(query_ordini_aperti)
                ordini_aperti = cursor.fetchall()
                columns_aperti = [col[0] for col in cursor.description]

                if ruolo_utente not in ['Logistica', 'Produzione']:
                    cursor.execute(query_ordini_chiusi)
                    ordini_chiusi = cursor.fetchall()
                    columns_chiusi = [col[0] for col in cursor.description]
            
            if ruolo_utente == "Produzione":
                ordini_aperti_dict = {}
                for riga in ordini_aperti:
                    if riga[4] == 'SOR' and riga[7] is not None:
                        continue
                    else:
                        ordini_aperti_dict[(riga[2], riga[3], riga[5])] = dict(zip(columns_aperti, riga))
                avanzamenti = Avanzamento_Ordini.objects.select_related('stato_ord', 'operatore').filter(operatore = request.user.id)
            else:
                ordini_aperti_dict = {
                    (riga[2], riga[3], riga[5]): dict(zip(columns_aperti, riga))
                    for riga in ordini_aperti
                }
                avanzamenti = Avanzamento_Ordini.objects.select_related('stato_ord', 'operatore')
            if ruolo_utente not in ['Logistica', 'Produzione']:
                ordini_chiusi_dict = {
                        (riga[2], riga[4], riga[6]): dict(zip(columns_chiusi, riga))
                        for riga in ordini_chiusi
                    }
            else:
                ordini_chiusi_dict = {}


            risultati_avanzamento_ordini = []
            risultati_ordini_da_pianificare = []
            risultati_storico_ordini = []

            for avanzamento in avanzamenti:
                if ruolo_utente == "Produzione":
                    tipo_uso = 'V'
                else:
                    ruolo = Profili.objects.get(ruolo=ruolo_utente)
                    tipo_uso = Profili_Stati.objects.filter(ruolo=ruolo, stato_ord=avanzamento.stato_ord).values_list('tipo_uso', flat=True)
                chiave = (
                    avanzamento.sede,
                    avanzamento.ordine,
                    avanzamento.n_riga,
                )
                # Calcola VIS_NOTE_ORD
                vis_note_ord = '' if avanzamento.fl_note_ord == 'N' else 'NOTE'

                # Calcola VIS_NOTE_PROD
                vis_note_prod = 'NOTE' if avanzamento.fl_note_prod == 'S' or avanzamento.fl_note_ord == 'S' else ''

                ordine_aperto = ordini_aperti_dict.get(chiave)
                ordine_chiuso = ordini_chiusi_dict.get(chiave)
                if ordine_aperto:
                    # Calcola DATA_CONS
                    data_sped = ordine_aperto.get('DATA_SPED')
                    data_ord = ordine_aperto.get('DATA_ORD')
                    if data_sped and data_ord:
                        if (data_sped - data_ord).days > 4:
                            data_cons = calcola_data_consegna(data_sped, 3)
                        else:
                            data_cons = data_sped
                    else:
                        data_cons = None 

                    if ordine_aperto.get('TIPO_ORDINE') != 'SOR' and ordine_aperto.get('ARTICOLO') is not None and 'V' in list(tipo_uso):
                        risultati_avanzamento_ordini.append({
                            'sede': avanzamento.sede,
                            'vis_note_ord': vis_note_ord,
                            'vis_note_prod': vis_note_prod,
                            'data_cons': str(data_cons) if data_cons else None,
                            'data_ord': str(data_ord) if data_ord else None,
                            'data_sped': str(data_sped) if data_sped else None,
                            'ordine': avanzamento.ordine,
                            'n_riga': int(avanzamento.n_riga),
                            'tipo_ordine': ordine_aperto.get('TIPO_ORDINE'),
                            'rif_cli': ordine_aperto.get('RIF_CLI'),
                            'articolo': ordine_aperto.get('ARTICOLO'),
                            'old_code': ordine_aperto.get('OLD_CODE'),
                            'des_articolo': ordine_aperto.get('DES_ARTICOLO'),
                            'qta_ord': int(ordine_aperto.get('QTA_ORD')),
                            'qta_cons': int(ordine_aperto.get('QTA_CONS')),
                            'qta_res': int(ordine_aperto.get('QTA_ORD') - ordine_aperto.get('QTA_CONS')),
                            'cd_cliente': ordine_aperto.get('CD_CLIENTE'),
                            'rif_int': ordine_aperto.get('RIF_INT'),
                            'des_cliente': ordine_aperto.get('DES_CLIENTE'),
                            'id_stato_ord': avanzamento.stato_ord.id,
                            'des_stato_ord': avanzamento.stato_ord.stato,
                            'operatore': avanzamento.operatore.username if avanzamento.operatore else None,
                            'des_operatore': avanzamento.operatore.nome if avanzamento.operatore else None,
                            'tipo_uso': list(tipo_uso),
                            'fl_note_ord': avanzamento.fl_note_ord,
                            'fl_note_prod': avanzamento.fl_note_prod,
                            'note_prod': avanzamento.note_prod,
                            'commerciale': ordine_aperto.get('COMMERCIALE'),
                        })

                    if ordine_aperto.get('TIPO_ORDINE') != 'SOR' and ordine_aperto.get('ARTICOLO') is not None and avanzamento.stato_ord.stato=='Da pianificare' and 'V' in list(tipo_uso):
                        risultati_ordini_da_pianificare.append({
                        'sede': avanzamento.sede,
                        'vis_note_ord': vis_note_ord,
                        'vis_note_prod': vis_note_prod,
                        'data_cons': str(data_cons) if data_cons else None,
                        'data_ord': str(data_ord) if data_ord else None,
                        'data_sped': str(data_sped) if data_sped else None,
                        'ordine': avanzamento.ordine,
                        'n_riga': int(avanzamento.n_riga),
                        'tipo_ordine': ordine_aperto.get('TIPO_ORDINE'),
                        'rif_cli': ordine_aperto.get('RIF_CLI'),
                        'articolo': ordine_aperto.get('ARTICOLO'),
                        'old_code': ordine_aperto.get('OLD_CODE'),
                        'des_articolo': ordine_aperto.get('DES_ARTICOLO'),
                        'qta_ord': int(ordine_aperto.get('QTA_ORD')),
                        'qta_cons': int(ordine_aperto.get('QTA_CONS')),
                        'qta_res': int(ordine_aperto.get('QTA_ORD') - ordine_aperto.get('QTA_CONS')),
                        'cd_cliente': ordine_aperto.get('CD_CLIENTE'),
                        'rif_int': ordine_aperto.get('RIF_INT'),
                        'des_cliente': ordine_aperto.get('DES_CLIENTE'),
                        'id_stato_ord': avanzamento.stato_ord.id,
                        'des_stato_ord': avanzamento.stato_ord.stato,
                        'operatore': avanzamento.operatore.username if avanzamento.operatore else None,
                        'des_operatore': avanzamento.operatore.nome if avanzamento.operatore else None,
                        'tipo_uso': list(tipo_uso),
                        'fl_note_ord': avanzamento.fl_note_ord,
                        'fl_note_prod': avanzamento.fl_note_prod,
                        'note_prod': avanzamento.note_prod,
                        'commerciale': ordine_aperto.get('COMMERCIALE'),
                    })
                    if ordine_chiuso:
                        # Calcola DATA_CONS
                        data_sped = ordine_chiuso.get('DATA_SPED')
                        data_ord = ordine_chiuso.get('DATA_ORD')
                        if data_sped and data_ord:
                            if (data_sped - data_ord).days > 4:
                                data_cons = calcola_data_consegna(data_sped, 3)
                            else:
                                data_cons = data_sped
                        else:
                            data_cons = None                                 
                        if ordine_chiuso.get('TIPO_ORDINE') != 'SOR' and ordine_chiuso.get('ARTICOLO') is not None and 'V' in list(tipo_uso):
                            risultati_storico_ordini.append({
                            'sede': avanzamento.sede,
                            'vis_note_ord': vis_note_ord,
                            'vis_note_prod': vis_note_prod,
                            'data_cons': str(data_cons) if data_cons else None,
                            'data_ord': str(data_ord) if data_ord else None,
                            'data_sped': str(data_sped) if data_sped else None,
                            'ordine': avanzamento.ordine,
                            'n_riga': int(avanzamento.n_riga),
                            'tipo_ordine': ordine_chiuso.get('TIPO_ORDINE'),
                            'rif_cli': ordine_chiuso.get('RIF_CLI'),
                            'articolo': ordine_chiuso.get('ARTICOLO'),
                            'old_code': ordine_chiuso.get('OLD_CODE'),
                            'des_articolo': ordine_chiuso.get('DES_ARTICOLO'),
                            'qta_ord': int(ordine_chiuso.get('QTA_ORD')),
                            'qta_cons': int(ordine_chiuso.get('QTA_CONS')),
                            'qta_res': int(ordine_chiuso.get('QTA_ORD') - ordine_chiuso.get('QTA_CONS')),
                            'cd_cliente': ordine_chiuso.get('CD_CLIENTE'),
                            'rif_int': ordine_chiuso.get('RIF_INT'),
                            'des_cliente': ordine_chiuso.get('DES_CLIENTE'),
                            'id_stato_ord': avanzamento.stato_ord.id,
                            'des_stato_ord': avanzamento.stato_ord.stato,
                            'operatore': avanzamento.operatore.username if avanzamento.operatore else None,
                            'des_operatore': avanzamento.operatore.nome if avanzamento.operatore else None,
                            'tipo_uso': list(tipo_uso),
                            'fl_note_ord': avanzamento.fl_note_ord,
                            'fl_note_prod': avanzamento.fl_note_prod,
                            'note_prod': avanzamento.note_prod,
                            'commerciale': ordine_chiuso.get('COMMERCIALE'),
                        })
                    else:
                        continue
                else:
                    if ordine_chiuso:
                        # Calcola DATA_CONS
                        data_sped = ordine_chiuso.get('DATA_SPED')
                        data_ord = ordine_chiuso.get('DATA_ORD')
                        if data_sped and data_ord:
                            if (data_sped - data_ord).days > 4:
                                data_cons = calcola_data_consegna(data_sped, 3)
                            else:
                                data_cons = data_sped
                        else:
                            data_cons = None                                 
                        if ordine_chiuso.get('TIPO_ORDINE') != 'SOR' and ordine_chiuso.get('ARTICOLO') is not None and 'V' in list(tipo_uso):
                            risultati_storico_ordini.append({
                            'sede': avanzamento.sede,
                            'vis_note_ord': vis_note_ord,
                            'vis_note_prod': vis_note_prod,
                            'data_cons': str(data_cons) if data_cons else None,
                            'data_ord': str(data_ord) if data_ord else None,
                            'data_sped': str(data_sped) if data_sped else None,
                            'ordine': avanzamento.ordine,
                            'n_riga': int(avanzamento.n_riga),
                            'tipo_ordine': ordine_chiuso.get('TIPO_ORDINE'),
                            'rif_cli': ordine_chiuso.get('RIF_CLI'),
                            'articolo': ordine_chiuso.get('ARTICOLO'),
                            'old_code': ordine_chiuso.get('OLD_CODE'),
                            'des_articolo': ordine_chiuso.get('DES_ARTICOLO'),
                            'qta_ord': int(ordine_chiuso.get('QTA_ORD')),
                            'qta_cons': int(ordine_chiuso.get('QTA_CONS')),
                            'qta_res': int(ordine_chiuso.get('QTA_ORD') - ordine_chiuso.get('QTA_CONS')),
                            'cd_cliente': ordine_chiuso.get('CD_CLIENTE'),
                            'rif_int': ordine_chiuso.get('RIF_INT'),
                            'des_cliente': ordine_chiuso.get('DES_CLIENTE'),
                            'id_stato_ord': avanzamento.stato_ord.id,
                            'des_stato_ord': avanzamento.stato_ord.stato,
                            'operatore': avanzamento.operatore.username if avanzamento.operatore else None,
                            'des_operatore': avanzamento.operatore.nome if avanzamento.operatore else None,
                            'tipo_uso': list(tipo_uso),
                            'fl_note_ord': avanzamento.fl_note_ord,
                            'fl_note_prod': avanzamento.fl_note_prod,
                            'note_prod': avanzamento.note_prod,
                            'commerciale': ordine_chiuso.get('COMMERCIALE'),
                        })
                    else:
                        continue       
    except Exception as e:
        error_msg = f"Errore con chiave {chiave}: {str(e)}"
        print(error_msg)
        print(traceback.format_exc())
        messages.error(request, error_msg)

    return risultati_avanzamento_ordini, risultati_ordini_da_pianificare, risultati_storico_ordini