import traceback
from collections import defaultdict
from .utils import calcola_data_consegna, riformatta_date
from datetime import datetime

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
    avanzamento_ordini = request.session.get('avanzamento_ordini')
    avanzamento_ordini_preferences = request.session.get('avanzamento_ordini_preferences')
    ruolo_utente = request.session.get('ruolo_utente')

    avanzamento_ordini_ref = riformatta_date(avanzamento_ordini)

    pagina = request.GET.get('pagina', '')
    tipo = request.GET.get('tipo', '')
    context = {
        'pagina': pagina, 
        'tipo': tipo,
        'ruolo_utente': ruolo_utente,
        'avanzamento_ordini': avanzamento_ordini_ref,
        'avanzamento_ordini_preferences': avanzamento_ordini_preferences,
    }
    
    return render(request, 'produzione/dashboard.html', context)

def get_avanzamento_ordini_preferences(avanzamento_ordini):
    
    # Inizializza set vuoti per raccogliere valori unici
    ordini_unici = set()
    clienti_unici = set()
    stati_unici = set()
    operatori_unici = set()

    # Un solo ciclo per popolare tutti i set
    for item in avanzamento_ordini:
        if item['ordine']:
            ordini_unici.add(item['ordine'])
        if item['des_cliente']:
            clienti_unici.add(item['des_cliente'])
        if item['des_stato_ord']:
            stati_unici.add(item['des_stato_ord'])
        if item['operatore']:
            operatori_unici.add(item['operatore'])

    # (Opzionale) Ordina i set convertendoli in liste
    ordini_unici = sorted(ordini_unici)
    clienti_unici = sorted(clienti_unici)
    stati_unici = sorted(stati_unici)
    operatori_unici = sorted(operatori_unici)
    
    return {
        ''
        'ordini_unici': ordini_unici,
        'clienti_unici': clienti_unici,
        'stati_unici': stati_unici,
        'operatori_unici': operatori_unici,
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
            
            ordini = [
                    Avanzamento_Ordini(
                        sede=row[0],
                        ordine=row[1],
                        n_riga=row[2],
                        stato_ord=row[3],
                        note=row[4]
                    )
                    for row in response_avanzamento_ordini
                ]
            
            Avanzamento_Ordini.objects.bulk_create(ordini, batch_size=1000)

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
                        .filter(Q(note__isnull=True) | Q(note=''))
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
                note = Note.objects.filter(SOHNUM_0=sohnum).first()
                if note and sohtex:
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT TEXTE_0 FROM PROD.TEXCLOB WHERE CODE_0 = %s", [sohtex])
                        row = cursor.fetchone()
                    
                    if row:
                        nuovo_testo = row[0]

                        if note.testo.strip() != nuovo_testo.strip():
                            note.testo = nuovo_testo
                            note.fl_upd = "S"
                            note.save()


            # 6. Accoda eventuali nuove note (non aggiornate)
            ordini = Avanzamento_Ordini.objects.exclude(note__isnull=True).exclude(note='') \
                    .values_list('sede', 'ordine', 'note')

            mappa = defaultdict(list)
            for sede, ordine, note in ordini:
                mappa[note].append((sede, ordine))
            codici = list(mappa.keys())

            if codici:
                placeholders = ','.join(['%s'] * len(codici))
                query = f"""
                    SELECT CODE_0, TEXTE_0
                    FROM PROD.TEXCLOB
                    WHERE CODE_0 IN ({placeholders})
                    AND TEXTE_0 LIKE '{{\\rtf1%'
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

def select_avanzamento_ordini(request, ruolo_utente):
    try:
        with transaction.atomic():            # 0.Accedi a sage
            connection = bsdb04_connection()

            # 1.Aggiorna Avanzamento Ordini
            with open(constant.C_QUERY_ORDINI_APERTI, 'r', encoding='utf-8') as file:
                query_ordini_aperti = file.read()

            with connection.cursor() as cursor:
                cursor.execute(query_ordini_aperti)
                ordini_aperti = cursor.fetchall()
                columns = [col[0] for col in cursor.description]
            
            if ruolo_utente == "Produzione":
                ordini_aperti_dict = {}
                for riga in ordini_aperti:
                    if riga[4] == 'SOR' and riga[7] is not None:
                        continue
                    else:
                        ordini_aperti_dict[(riga[2], riga[3], riga[5])] = dict(zip(columns, riga))
                avanzamenti = Avanzamento_Ordini.objects.select_related('stato_ord', 'operatore').filter(operatore = request.user.id)
            else:
                ordini_aperti_dict = {
                    (riga[2], riga[3], riga[5]): dict(zip(columns, riga))
                    for riga in ordini_aperti
                }

                avanzamenti = Avanzamento_Ordini.objects.select_related('stato_ord', 'operatore')

        
            risultati = []
            
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

                ordine_aperto = ordini_aperti_dict.get(chiave)
                if not ordine_aperto:
                    continue
                
                # Calcola VIS_NOTE_ORD
                vis_note_ord = '' if avanzamento.fl_note_ord == 'N' else 'NOTE'

                # Calcola VIS_NOTE_PROD
                vis_note_prod = 'NOTE' if avanzamento.fl_note_prod == 'S' or avanzamento.fl_note_ord == 'S' else ''

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

                risultati.append({
                    'sede': avanzamento.sede,
                    'vis_note_ord': vis_note_ord,
                    'vis_note_prod': vis_note_prod,
                    'data_cons': str(data_cons) if data_cons else None,
                    'data_ord': str(data_ord) if data_ord else None,
                    'data_sped': str(data_sped) if data_sped else None,
                    'ordine': avanzamento.ordine,
                    'n_riga': avanzamento.n_riga,
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
    except Exception as e:
        error_msg = f"Errore con chiave {chiave}: {str(e)}"
        print(error_msg)
        print(traceback.format_exc())
        messages.error(request, error_msg)
    
    return risultati 