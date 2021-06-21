from sqlalchemy import func, text
from app import db
from app.exceptions import UnsupportedDatabaseEngineError


def within_interval(date1, date2, days_interval):
    """
    Check whether `date2` is less than `interval` of `date1`

    Parameters
    ----------
    date1 : db.Column(date)
        The first date
    date2 : db.Column(date)
        The second date
    days_interval : int
        An interval in number of days
    """
    if db.engine.name == 'sqlite':
        days_diff = func.julianday(date2) - func.julianday(date1)
    elif db.engine.name == 'mssql':
        days_diff = func.datediff(text('day'), date1, date2)
    else:
        raise UnsupportedDatabaseEngineError("Unsupported database engine '{}'"
                                             .format(db.engine.name))
    return days_diff <= days_interval
