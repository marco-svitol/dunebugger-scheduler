from dunebugger_settings import settings
from mqueue import NATSComm
from mqueue_handler import MessagingQueueHandler
from schedule_interpreter import ScheduleInterpreter

mqueue_handler = MessagingQueueHandler()

mqueue = NATSComm(
    nat_servers=settings.mQueueServers,
    client_id=settings.mQueueClientID,
    subject_root=settings.mQueueSubjectRoot,
    mqueue_handler=mqueue_handler,
)
schedule_interpreter = ScheduleInterpreter(mqueue_handler)
mqueue_handler.schedule_interpreter = schedule_interpreter
mqueue_handler.mqueue_sender = mqueue
