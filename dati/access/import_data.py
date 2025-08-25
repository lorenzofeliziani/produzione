import pyodbc
import django
import os
import csv

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


def update_avanzamento_ordini():
    Avanzamento_Ordini.objects.all().delete()

    csv_path = '/home/screen/gestioneProduzioneTest/ultimiDatiAccess/AVANZAMENTO_ORDINI.csv'

    with open(csv_path, newline='', encoding='windows-1252') as csvfile:
        reader = csv.reader(csvfile, delimiter=';')

        for row in reader:
            if not row: 
                continue

            try:
                stato_id = row[3] 
                operatore_username = row[4]  

                stato = Stati_Ordini.objects.filter(id=stato_id).first()
                operatore = Utenti.objects.filter(username=operatore_username).first()

                avanzamento = Avanzamento_Ordini(
                    sede=row[0],
                    ordine=row[1],
                    n_riga=int(row[2]),
                    stato_ord=stato,
                    operatore=operatore,
                    note=row[5] if row[5] else '',
                    note_prod=row[6] if row[6] else '',
                    fl_note_prod=(row[7] if row[7] else 'N').upper(),
                    fl_note_ord=(row[8] if row[8] else 'N').upper(),
                    all_ord=row[9] if row[9] else '',
                )

                avanzamento.save()
            except Exception as e:
                print(f"Errore nella riga: {row} - {e}")

    print("Importazione completata.")


def import_profili_stati():
    # Imposta il contesto Django
    Profili_Stati.objects.all().delete()
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