from dunebugger_settings import settings
from mqueue import NATSComm
from mqueue_handler import MessagingQueueHandler
from scheduler_service import SchedulerService

mqueue_handler = MessagingQueueHandler()
mqueue = NATSComm(
    nat_servers=settings.mQueueServers,
    client_id=settings.mQueueClientID,
    subject_root=settings.mQueueSubjectRoot,
    mqueue_handler=mqueue_handler,
)

mqueue_handler.mqueue_sender = mqueue
scheduler_service = SchedulerService()
scheduler_service.set_message_handler(mqueue_handler)
# Monitor will be started asynchronously in main.py
