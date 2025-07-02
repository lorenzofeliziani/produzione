# appLogger.py

from pathlib import Path
import os
import logging

# Percorso dinamico del file di log
if os.name == 'nt':  # Windows
    log_path = os.path.join(Path(__file__).resolve().parent.parent.parent, 'log', 'produzione.log')
else:  # Linux / Unix
    log_path = '/var/log/produzione.log'

# Configurazione base del logging
logging.basicConfig(
    level=logging.INFO,
    filename=log_path,
    format='%(asctime)s %(name)s [%(levelname)s] %(message)s',
    filemode='a',  # append al file di log
)

# Funzione per ottenere il logger nel modulo che lo importa
def get_logger(name=__name__):
    return logging.getLogger(name)