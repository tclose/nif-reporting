"""
Constants used throughout the database
"""


ADMIN = 1

USER_ROLES = {
    ADMIN: ('Admin', 'Admin team')}


DISABLED_USER = 0
ENABLED_USER = 1
NEW_USER = 2

USER_STATUS = {
    DISABLED_USER: ('Disabled', "Disabled/not-activated user"),
    ENABLED_USER: ('Enabled', "Enabled user"),
    NEW_USER: ('New', "hasn't been enabled yet"),
}
