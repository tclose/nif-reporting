from functools import wraps
from flask import g, flash, redirect, url_for, request, has_app_context
from app import app
from .constants import ENABLED_USER, USER_ROLES


def requires_login(role_id=None):
    """
    Checks to see whether the user has been logged in and has the right role
    IDs
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            accepted = False
            if g.user is None:
                flash('You need to be signed in to access that page.',
                      'info')
            elif g.user.status != ENABLED_USER:
                flash(("Your user account has been created but still needs "
                       + "to be activiated, please contact {}").format(
                           app.config['ADMIN_EMAIL']),
                      'warning')
            elif role_id is not None and not g.user.is_authorised(role_id):
                flash(("'{}' doesn't have the role '{}', which is required "
                       + "to access this page (they have '{}')").format(
                           g.user.email, USER_ROLES[role_id][0],
                           "', '".join(str(r.name) for r in g.user.roles)),
                      'error')
            else:
                accepted = True
            if not accepted:
                return redirect(
                    url_for('login', next='{}?{}'.format(
                        request.path, request.query_string.decode('utf-8'))))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def with_app_context(f):
    @wraps(f)
    def wrapped_f(*args, **kwargs):
        if not has_app_context():
            with app.app_context():
                return f(*args, **kwargs)
        else:
            return f(*args, **kwargs)
    return wrapped_f
