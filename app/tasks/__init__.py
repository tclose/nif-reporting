from celery.schedules import crontab
from app import celery


@celery.on_after_configure.connect
def schedule(sender, **kwargs):  # pylint: disable=unused-argument
    """
    Specify frequency of periodic tasks
    """
    # Email summary of reports for each affiliation
    # sender.add_periodic_task(
    #     crontab(minute=0, hour=9, day_of_month=1),
    #     task,
    #     name='task_name')
