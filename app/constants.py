"""
Constants used throughout the database
"""


ADMIN_USER_ROLE = 1

USER_ROLE = {
    ADMIN_USER_ROLE: ('Admin', 'Admin team')}


DISABLED_USER_STATUS = 0
ENABLED_USER_STATUS = 1
NEW_USER_STATUS = 2

USER_STATUS = {
    DISABLED_USER_STATUS: ('Disabled', "Disabled/not-activated user"),
    ENABLED_USER_STATUS: ('Enabled', "Enabled user"),
    NEW_USER_STATUS: ('New', "hasn't been enabled yet"),
}

UNKNOWN_ACCESS_CONTENT = -1
CANT_ACCESS_CONTENT = 0
PLAIN_TEXT_ACCESS_CONTENT = 1
HTML_ACCESS_CONTENT = 2
PDF_ACCESS_CONTENT = 3


ACCESS_CONTENT = {
    UNKNOWN_ACCESS_CONTENT: ("Unknown access", "Unknown location of content"),
    CANT_ACCESS_CONTENT: ("Can't access",
                          "No automated/authorised access to conent"),
    PLAIN_TEXT_ACCESS_CONTENT: ("Plain text access",
                                "Plain text accessible via ScienceDirect API"),
    HTML_ACCESS_CONTENT: ("HTML access",
                          "HTML directly accessible directly using DOI"),
    PDF_ACCESS_CONTENT: ("PDF access", "PDF accessible via Wiley Online API")
}


NO_NIF_ASSOC = 0
UNLIKELY_NIF_ASSOC = 10
POSSIBLE_NIF_ASSOC = 20
PROBABLE_NIF_ASSOC = 30
HIGHLY_PROBABLE_NIF_ASSOC = 40
DEFINITE_NIF_ASSOC = 50

NIF_ASSOC = {
    NO_NIF_ASSOC: ('Not', 'Not associated with NIF'),
    UNLIKELY_NIF_ASSOC: ('Unlikely', 'Unlikely to be associated with NIF'),
    POSSIBLE_NIF_ASSOC: ('Possible', 'Possibly associated with NIF'),
    PROBABLE_NIF_ASSOC: ('Probable', 'Probably associated with NIF'),
    HIGHLY_PROBABLE_NIF_ASSOC: (
        'Highly probable',
        'Higly probable to be associated with NIF. Manually checked but '),
    DEFINITE_NIF_ASSOC: ('Definite', 'Definitely associated with NIF')}
