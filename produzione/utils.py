from datetime import timedelta, datetime


def calcola_data_consegna(data_inizio, giorni):
    data_corrente = data_inizio
    while giorni > 0:
        data_corrente -= timedelta(days=1)
        if data_corrente.weekday() < 5:  # 0 = lunedì, 6 = domenica
            giorni -= 1
    return data_corrente

def converti_datetime_in_str(lista_dict):
    for item in lista_dict:
        for chiave, valore in item.items():
            if isinstance(valore, (datetime,)):
                item[chiave] = valore.isoformat()
    return lista_dict


def riformatta_date(avanzamento_ordini):
    for ordine in avanzamento_ordini:
        if ordine['data_cons']:
            ordine['data_cons'] = datetime.fromisoformat(ordine['data_cons'])

        if ordine['data_ord']:
            ordine['data_ord'] = datetime.fromisoformat(ordine['data_ord'])

        if ordine['data_sped']:
            ordine['data_sped'] = datetime.fromisoformat(ordine['data_sped'])
    
    return avanzamento_ordini