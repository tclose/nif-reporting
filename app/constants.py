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