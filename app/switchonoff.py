#!/usr/bin/python3
import schedule
import time
import subprocess
from datetime import time as dtime
from datetime import datetime
from itertools import tee, islice, chain
from InTime import check_ntp_sync  # , getNTPTime
import sys
from os import path
from dunebugger_logging import logger

parentDir = path.join(path.dirname(path.abspath(__file__)), "..")
# Add the parent directory to sys.path
sys.path.append(parentDir)

mainModule = "main.py"
onseq = [dtime(8, 55), dtime(14, 55)]
offseq = [dtime(12, 30), dtime(19, 30)]
onoffsorted = []
timesyncJob = None
mainpaneid = ""
showoffsched = False
showonsched = False

# TODO verific timesync su orologio hw
# TODO forza switch on tramite tree state


def tmuxSendCommandToPane(command, key=""):
    tmuxCommand = ["tmux", "send-keys", "-t", mainpaneid, command, key]
    subprocess.Popen(tmuxCommand)


def tmuxNewPane():
    global mainpaneid
    cmd = ["tmux", "split-window", "-h", "-c", parentDir]
    subprocess.Popen(cmd).wait()  # Wait for the pane to be created

    # Get the pane ID of the last pane created
    cmd = ["tmux", "display-message", "-p", "#{pane_id}"]
    mainpaneid = subprocess.check_output(cmd).decode("ascii").strip()


def switchon():
    global showoffsched
    logger.info("Switching on dunebugger")
    tmuxSendCommandToPane("##", "ENTER")
    mainModulePath = path.join(parentDir, mainModule)
    tmuxSendCommandToPane("python " + mainModulePath, "ENTER")
    showoffsched = True


def switchoff():
    global showonsched
    if timeSyncJobIsRunning():
        logger.warning("Time not synced, scheduled switching off not done")
    else:
        logger.info("Switching off dunebugger")
        tmuxSendCommandToPane("C-c")
    showonsched = True


def set_prompt():
    tmuxSendCommandToPane("export PS1='>'", "C-m")


def previous_and_next(some_iterable):
    prevs, items, nexts = tee(some_iterable, 3)
    prevs = chain([None], prevs)
    nexts = chain(islice(nexts, 1, None), [None])
    return zip(prevs, items, nexts)


def sortonoff():
    global onseq, offseq, onoffsorted

    if offseq[0] == dtime(0, 0):  # se lo spegnimento è alle 0:0 è troppo complesso da gestire e lo sposto avanti un minuto. Muore nessuno dai.
        offseq[0] = dtime(0, 1)

    onseq.sort()
    offseq.sort()

    if onseq[len(onseq) - 1] > offseq[len(offseq) - 1] and offseq[0] != dtime(0, 0):  # se finisce con un'accensione allora aggiungo accensione a mezzanotte
        onseq.insert(0, dtime(0, 0))

    onoffsorted = [onseq[0]]

    for _previous, item, nxt in previous_and_next(onseq):
        for ofs in offseq:
            if nxt is not None:
                if item < ofs < nxt:
                    onoffsorted.extend([ofs, nxt])
                    break
            else:
                if item < ofs:
                    onoffsorted.extend([ofs])
                    break


def checktimeon(d):
    if d < onoffsorted[0]:  # now è prima della prima accensione
        return False
    elif d > onoffsorted[len(onoffsorted) - 1]:  # se sono oltre l'ultimo orario verifico se l'ultimo item è accen o spegn
        if len(onoffsorted) % 2 == 0:  # se pari allora ultimo è spegnimento
            return False
        else:
            return True  # se invece dispari l'ultimo è accensione
    i = 1
    for _previous, item, nxt in previous_and_next(onoffsorted):
        if item < d < nxt and i % 2 == 0:
            return False
        i += 1
    return True


def timeSyncJobIsRunning():
    if timesyncJob:
        return timesyncJob.is_job_cancelled()
    else:
        return False


def checkTimeSync():
    # nettime = getNTPTime()
    if check_ntp_sync():
        # if isinstance(nettime,int): #check Internet time sync
        # logging.info("Time successfully synced from the net:"+time.ctime(nettime))
        logger.info(f"Time successfully synced {datetime.now().strftime('%H:%M:%S')}")
        if timeSyncJobIsRunning():
            logger.info("Removing timesync job from scheduling")
            schedule.cancel_job(timesyncJob)
            checktimeonandswitch()
    else:
        logger.warning("Time syncing failed!")


def checktimeonandswitch():
    if checktimeon(datetime.now().time()):  # check if current time dunebugger should be on
        logger.info("Current time is after a switch on and before a switch off: switching on")
        switchon()
    else:
        logger.info("Current time is after a switch off and before a switch on: switching off")
        switchoff()


def main():
    logger.info("Dunebugger supervisor started")
    global showoffsched
    global showonsched
    timesyncsleep = 10
    timesyncmin = 180
    timesyncmax = 200
    checkinterval = 20  # checkscheduling interval

    tmuxNewPane()  # creates new tmux pane and set ID num
    time.sleep(1)
    set_prompt()

    logger.info("Checking if time sync is available...")

    # nettime = getNTPTime() #check Internet time sync
    # if not isinstance(nettime,int):
    if not check_ntp_sync():
        logger.warning("Not syncing first try...waiting " + str(timesyncsleep) + " secs")
        time.sleep(timesyncsleep)
        # nettime = getNTPTime()
        # verify another another time. If still not syncing run a scheduled job and switch on the presepe
        # if not isinstance(nettime,int):
        if not check_ntp_sync():
            logger.warning("time not synced at startup: scheduling timesyncjob with random frequency between " + str(timesyncmin) + " secs and " + str(timesyncmax) + " secs")
            # timesyncJob = schedule.every(timesyncmin).to(timesyncmax).seconds.do(checkTimeSync)
            # fo = open(installfolder+"timenotsynced", "wb") #tells dunebugger that syncing is not working....
            # fo.close()
    # if isinstance(nettime,int):
    if check_ntp_sync():
        logger.info(f"...time sync ok. Time is {datetime.now().strftime('%H:%M:%S')}")
        # logger.info("...time sync ok. Time is "+time.ctime(nettime))

    sortonoff()  # sort, merge and clean on off sequence

    if timeSyncJobIsRunning():
        # if time is not syncing switch on and warning
        logger.warning("Time not synced, forcefully switching on")
        switchon()
    else:
        # if time is synced check scheduling
        checktimeonandswitch()

    # se dispari, se index0 == 0:0 allora parte con spegnimento all'index1
    starton = 0
    if len(onoffsorted) % 2 != 0:
        starton = 1
        onoffsorted.pop(0)

    for ind, onoff in enumerate(onoffsorted):
        if ind % 2 == starton:
            logger.debug("Adding SwitchOn scheduling at " + str(onoff))
            schedule.every().day.at(str(onoff)).do(switchon)
        else:
            logger.debug("Adding SwitchOff scheduling at " + str(onoff))
            schedule.every().day.at(str(onoff)).do(switchoff)

    logger.info("Checking scheduling every " + str(checkinterval) + " seconds")

    while True:
        time.sleep(checkinterval)  # check scheduling every checkinterval seconds
        schedule.run_pending()
        if timeSyncJobIsRunning():
            showoffsched = False
            showonsched = False
        else:
            if showoffsched:
                logger.info("Next scheduled switchOFF at " + str(schedule.next_run()))
                showoffsched = False
            if showonsched:
                logger.info("Next scheduled switchON at " + str(schedule.next_run()))
                showonsched = False


if __name__ == "__main__":
    main()
