"""
Usefull constant for Produzione
"""

from pathlib import Path
import os

if os.name == 'nt':
    C_QUERY_AVANZAMENTO_ORDINI = os.path.join(Path(__file__).resolve().parent.parent, 'dati/sage/queries/avanzamento_ordini.sql')
    C_QUERY_X_NOTE = os.path.join(Path(__file__).resolve().parent.parent, 'dati/sage/queries/x_note.sql')
    C_QUERY_ORDINI_APERTI = os.path.join(Path(__file__).resolve().parent.parent, 'dati/sage/queries/ordini_aperti.sql')
    C_QUERY_ORDINI_CHIUSI = os.path.join(Path(__file__).resolve().parent.parent, 'dati/sage/queries/ordini_chiusi.sql')
else:
    C_QUERY_AVANZAMENTO_ORDINI = '/home/screen/Produzione/dati/sage/queries/avanzamento_ordini.sql'
    C_QUERY_X_NOTE = '/home/screen/Produzione/dati/sage/queries/x_note.sql'
    C_QUERY_ORDINI_APERTI = '/home/screen/Produzione/dati/sage/queries/ordini_aperti.sql'
    C_QUERY_ORDINI_CHIUSI = '/home/screen/Produzione/dati/sage/queries/ordini_chiusi.sql'