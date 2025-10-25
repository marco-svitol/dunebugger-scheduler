from datetime import date
from datetime import datetime
from datetime import time as dtime
from datetime import timedelta
import sys
from os import path
from dunebugger_logging import logger
import subprocess

# Get parent directory
parent_dir = path.join(path.dirname(path.abspath(__file__)), "..")
# Add the parent directory to sys.path
sys.path.append(parent_dir)


def check_ntp_sync():
    try:
        # Run the timedatectl command and capture the output
        result = subprocess.run(["timedatectl", "status"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            # Check if NTP is synchronized
            if "synchronized: yes" in result.stdout:
                return True
            else:
                return False
        else:
            logger.error(f"Error running timedatectl: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Error running timedatectl: ${str(e)}")
        return False


# TODO: cyclelength must be the last event in main sequence
def duranteCelebrazioni(dt, cyclelength):
    tday = dt.date()
    wday = tday.weekday()  # 0 lun ... 6 domenica
    ctime = dtime(dt.time().hour, dt.time().minute)  # HH : MM
    # print(tday)
    # print(wday)
    # print (ctime)

    festivi = [  # Mese Giorno
        datetime.strptime("12 25", "%m %d").date().replace(year=date.today().year),
        datetime.strptime("12 24", "%m %d").date().replace(year=date.today().year),
        datetime.strptime("01 01", "%m %d").date().replace(year=date.today().year),
        datetime.strptime("01 06", "%m %d").date().replace(year=date.today().year),
        datetime.strptime("01 27", "%m %d").date().replace(year=date.today().year),  # aggiunto temporaneamente Lunedì 27/1/2020
    ]

    messeprefestive = [  # Ora minuti
        dtime(8, 0),
        dtime(16, 0),  # adorazione
        dtime(16, 30),
        dtime(17, 0),
        dtime(17, 30),
        dtime(18, 0),  # vespri
    ]

    messefestive = [  # Ora minuti
        dtime(8, 0),
        dtime(9, 30),
        dtime(11, 15),
        dtime(18, 0),
        dtime(20, 30),  # modificato da 20:30 a 20:45 per lunedì 27/1/2020
        # dtime(21,25), #aggiunto per lunedì 27/1/2020
        # dtime(23,0), #messa mezzanotte dalle 23 alla 1
        # dtime(23,40)#, tolto per messa 31/12 23.30
        # dtime(0,10)
    ]

    messeferiali = [  # Ora minuti
        dtime(8, 0),
        dtime(18, 0),
        # dtime(20,55), #aggiunto per catechesi lunedì
        # dtime(21,24),
        # dtime(21,53),
        # dtime(22,10),
        # dtime(23,29) #aggiunto per messa 31/12....confronto orario non può andare oltre il giorno!! oppure modifica confronto
    ]

    duratamessafestiva = 40  # minuti
    duratamessaferiale = 30  # minuti

    try:  # verifica se in elenco giorni festivi
        cfestivo = festivi.index(tday)
    except Exception:
        cfestivo = -1

    # print(cfestivo)
    if wday == 5 and cfestivo < 0:  # se sabato allora verifico se in orario messa prefest
        # print ("sabato")
        for mprefes in messeprefestive:
            if (datetime.combine(date(1, 1, 1), mprefes) - timedelta(seconds=cyclelength)).time() <= ctime <= (datetime.combine(date(1, 1, 1), mprefes) + timedelta(minutes=duratamessafestiva)).time():
                return True
    elif wday == 6 or cfestivo >= 0:  # se domenica o festivo allora verifico se in orario messa domenicale
        for mfes in messefestive:
            if (datetime.combine(date(1, 1, 1), mfes) - timedelta(seconds=cyclelength)).time() <= ctime <= (datetime.combine(date(1, 1, 1), mfes) + timedelta(minutes=duratamessafestiva)).time():
                return True
    else:  # allora feriale (pre-festivo suppongo uguale a messa feriale)
        for mfer in messeferiali:
            # print (str(ctime) + " " + str((datetime.combine(date(1,1,1),mfer)-timedelta(seconds=cyclelength)).time())+ " " + str((datetime.combine(date(1,1,1),mfer)+timedelta(minutes=duratamessaferiale)).time()))
            if (datetime.combine(date(1, 1, 1), mfer) - timedelta(seconds=cyclelength)).time() <= ctime <= (datetime.combine(date(1, 1, 1), mfer) + timedelta(minutes=duratamessaferiale)).time():
                return True
    return False
