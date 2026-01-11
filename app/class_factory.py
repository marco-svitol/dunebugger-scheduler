from dunebugger_settings import settings
from state_tracker import state_tracker
from ntp_status import NTPStatusManager
from mqueue import NATSComm
from mqueue_handler import MessagingQueueHandler
from schedule_interpreter import ScheduleInterpreter

mqueue_handler = MessagingQueueHandler()
ntp_status_manager = NTPStatusManager()

mqueue = NATSComm(
    nat_servers=settings.mQueueServers,
    client_id=settings.mQueueClientID,
    subject_root=settings.mQueueSubjectRoot,
    mqueue_handler=mqueue_handler,
)
schedule_interpreter = ScheduleInterpreter(mqueue_handler, state_tracker, ntp_status_manager)
mqueue_handler.schedule_interpreter = schedule_interpreter
mqueue_handler.mqueue_sender = mqueue
mqueue_handler.ntp_status_manager = ntp_status_manager
state_tracker.mqueue_handler = mqueue_handler