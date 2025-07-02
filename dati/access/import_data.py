import pyodbc
import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestionale.settings')

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

django.setup()

from produzione.models import Avanzamento_Ordini, Stati_Ordini, Utenti, Profili, Profili_Stati


def import_utenti():
  # Assicurati di usare il path corretto

    conn_str = r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=C:\Users\lorif\OneDrive\Desktop\DB\Produzione_old\Last Version\Produzione.accdb;'
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM UTENTI")
    utenti_rows = cursor.fetchall()
    utenti_columns = [col[0] for col in cursor.description]

    for row in utenti_rows:
        data = dict(zip(utenti_columns, row))
        id = int(data['id_utente'])
        username = data['username']
        nome = data.get('ds_utente', '')
        fl_ope = data.get('fl_ope', 'N') or 'N'

        # Ricava il ruolo
        cursor.execute("""
            SELECT A.DES_PROFILO
            FROM PROFILI_UTENTI AS A
            INNER JOIN LNK_UTENTI_PROFILI AS B ON B.ID_PROFILO_USR = A.ID_PROFILO_USR
            WHERE B.USRNAME = ?
        """, username)
        ruolo_row = cursor.fetchone()
        ruolo = ruolo_row.DES_PROFILO if ruolo_row else None

        # Crea o aggiorna utente
        user_obj = Utenti.objects.filter(id=id).first()
        if not user_obj:
            user_obj = Utenti(id=id, username=username)
        
        user_obj.nome = nome
        user_obj.ruolo = ruolo
        user_obj.fl_ope = fl_ope
        if not user_obj.has_usable_password():
            user_obj.set_password("password")
        user_obj.save()

    print("Utenti importati correttamente.")


def import_avanzamento_ordini():
    # Imposta il contesto Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nome_progetto.settings')
    django.setup()

    # Connessione a Access
    conn_str = r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=C:\Users\lorif\OneDrive\Desktop\DB\Produzione_old\Last Version\Produzione.accdb;' 
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    # Query alla tabella Access
    cursor.execute("SELECT * FROM AVANZAMENTO_ORDINI")
    rows = cursor.fetchall()

    # Colonne della tabella
    columns = [column[0] for column in cursor.description]

    # Inserimento dati
    for row in rows:
        data = dict(zip(columns, row))
        stato = Stati_Ordini.objects.filter(id=data['ID_STATO_ORD']).first()
        operatore = Utenti.objects.filter(username=data['OPERATORE']).first()

        # Crea record Django
        avanzamento = Avanzamento_Ordini(
            sede=data['CPY_0'],
            ordine=data['SOHNUM_0'],
            n_riga=data['SOPLIN_0'],
            stato_ord=stato,
            operatore=operatore,
            note=data.get('SOHTEX1_0', '') ,
            note_prod=data.get('NOTE_PROD', ''),
            fl_note_prod=data.get('FL_NOTE_PROD', 'N') or 'N',
            fl_note_ord=data.get('FL_NOTE_ORD', 'N') or 'N',
            all_ord=data.get('ALL_ORD', '')
        )
        avanzamento.save()

    print("Importazione completata.")

def import_profili_stati():
    # Imposta il contesto Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nome_progetto.settings')
    django.setup()

    # Connessione a Access
    conn_str = r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=C:\Users\lorif\OneDrive\Desktop\DB\Produzione_old\Last Version\Produzione.accdb;' 
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    # Query alla tabella Access
    cursor.execute("SELECT * FROM LNK_PROFILI_STATI")
    rows = cursor.fetchall()

    # Colonne della tabella
    columns = [column[0] for column in cursor.description]

    # Inserimento dati
    for row in rows:
        data = dict(zip(columns, row))
        ruolo = Profili.objects.filter(id=data['ID_PROFILO_USR']).first()
        stato_ord = Stati_Ordini.objects.filter(id=data['ID_STATO_ORD']).first()

            # Crea record Django
        profili_stati = Profili_Stati(
            ruolo=ruolo,
            stato_ord=stato_ord,
            tipo_uso=data.get('TIPO_USO', 'V') or 'V'
        )
        profili_stati.save()

    print("Importazione completata.")

import_profili_stati()