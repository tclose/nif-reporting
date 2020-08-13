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

CANT_ACCESS_FULL_TEXT = 0
PII_ACCESS_FULL_TEXT = 1
HTML_ACCESS_FULL_TEXT = 2
PDF_ACCESS_FULL_TEXT = 3


ACCESS_FULL_TEXT = {
    CANT_ACCESS_FULL_TEXT: ("Can't access", "No automated access to full text"),
    PII_ACCESS_FULL_TEXT: ("PII access", "Accessible via ScienceDirect API"),
    HTML_ACCESS_FULL_TEXT: ("HTML access",
                            "HTML accessible directly using DOI"),
    PDF_ACCESS_FULL_TEXT: ("PDF access", "PDF accessible via Wiley Online API")
}

NO_NIF_ASSOC = 0
UNLIKELY_NIF_ASSOC = 10
POSSIBLE_NIF_ASSOC = 20
PROBABLE_NIF_ASSOC = 30
DEFINITE_NIF_ASSOC = 50

NIF_ASSOC = {
    NO_NIF_ASSOC: ('No association', 'Not associated with NIF'),
    UNLIKELY_NIF_ASSOC: ('Unlikely', 'Unlikely to be associated with NIF'),
    POSSIBLE_NIF_ASSOC: ('Possible', 'Possibly associated with NIF'),
    PROBABLE_NIF_ASSOC: ('Probable', 'Probably associated with NIF'),
    DEFINITE_NIF_ASSOC: ('Definite', 'Definitely associated with NIF')}
