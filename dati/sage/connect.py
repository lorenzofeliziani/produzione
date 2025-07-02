import os
import pyodbc
import sqlserverport
from time import sleep
from .appLogger import get_logger

logger = get_logger(__name__)

logger.info("Inizio funzione dashboard")

def bsdb04_connection():
    return bsdb04_connection_windows() if os.name == 'nt' else bsdb04_connection_linux()

def bsdb04_connection_windows():
    """ * """
    server = r'sagex3\SAGEX3P'
    database = 'x3'
    username = 'reader'
    password = 'read$Only'

    return pyodbc.connect('Driver={SQL Server};'
                          'Server='+server+';'
                          'Database='+database+';'
                          'Trusted_Connection=no;'
                          'UID='+username+';'
                          'PWD='+password)

def bsdb04_connection_linux():
    """ * """
    servername = 'sagex3.dbelettronica.local'
    instancename = 'SAGEX3P'
    database = 'x3'
    username = 'reader'
    password = 'read$Only'

    ## Try 4 time with 2 second wait beetwen
    sleep_time = 2
    num_retries = 4
    for num_retry in range(0, num_retries):
        
        try:
            # my problematic function
            serverspec = '{0},{1}'.format(servername,
                                          sqlserverport.lookup(servername, instancename))
            str_error = None
        except Exception as err:
            logger.warning(f"Eccezione {err}, tentativo {num_retry} della funzione 'serverspec'")
            str_error = err
            pass

        if str_error:
            print(str_error)
            sleep(sleep_time)
            sleep_time *= 2
        else:
            break

    return pyodbc.connect('Driver=ODBC Driver 17 for SQL Server;Server={0};Database={1};'
                          'Trusted_Connection=no;UID={2};PWD={3}'.format(serverspec,
                                                                         database,
                                                                         username,
                                                                         password))