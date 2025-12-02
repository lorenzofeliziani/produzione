from datetime import timedelta, datetime, date

def split_list(value, sep=","):
        return [v.strip() for v in value.split(sep)] if value else []

def parse_dates(value):
        if value:
            result = []
            for v in split_list(value):
                single_v = split_list(v, '->')
                start = single_v[0]
                end = single_v[1] 
                result.append([start, end])
            return result
        else:
            return []

def match_or(field, values):
    if not values:
        return True
    field_val = (field or "").lower()
    return any(v.lower() in field_val for v in values)

def match_or_date_ranges(date_value, values):
    if not values:
        return True
    for value in values:
        s = datetime.fromisoformat(value[0]).date() if value[0] else ''
        e = datetime.fromisoformat(value[1]).date() if value[1] else ''
        if (not s or date_value >= s) and (not e or date_value <= e):
            return True
    return False

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
            ordine['data_cons'] = datetime.fromisoformat(ordine['data_cons']).date()

        if ordine['data_cons_eff']:
            ordine['data_cons_eff'] = datetime.fromisoformat(ordine['data_cons_eff']).date()

        if ordine['data_ord']:
            ordine['data_ord'] = datetime.fromisoformat(ordine['data_ord']).date()

        if ordine['data_sped']:
            ordine['data_sped'] = datetime.fromisoformat(ordine['data_sped']).date()
    
    return avanzamento_ordini

def riformatta_date_groups(ordini):
    for ordine in ordini:
        if ordine['data_cons']:
            ordine['data_cons'] = datetime.fromisoformat(ordine['data_cons']).date()
        if ordine['data_cons_eff']:
            ordine['data_cons_eff'] = datetime.fromisoformat(ordine['data_cons_eff']).date()
        for riga in ordine['dati']:
            if riga['data_cons']:
                riga['data_cons'] = datetime.fromisoformat(riga['data_cons']).date()
                
            if riga['data_cons_eff']:
                riga['data_cons_eff'] = datetime.fromisoformat(riga['data_cons_eff']).date()

            if riga['data_ord']:
                riga['data_ord'] = datetime.fromisoformat(riga['data_ord']).date()

            if riga['data_sped']:
                riga['data_sped'] = datetime.fromisoformat(riga['data_sped']).date()
    
    return ordini