NIF Reporting
=============

A set of tools to assist generating data for NIF reporting

Detecting publications of users 
-------------------------------

There is a table of key users (i.e. CIs) in the ``databases/app.db`` database,
which are used to search Scopus for any publications in the current reporting
period. The scripts used to do this are:

* ``scripts/add_authors.py`` - add new potential authors (CIs) along with their Scopus IDs to the database. Will need to be manually checked afterwards and incorrect matches removed manually
* ``scripts/add_pubs.py`` - find all pubs by the authors in the DB for the current year (unless otherwise specified)
* ``scripts/add_content.py`` - download full text copies for the pubs in the database where possible
* ``scripts/guess_nif_assoc.py`` - guess whether the publication is associated with the iMed GE (based on dumb text search) and return results in a CSV
* ``scripts/export_csv.py`` - after publications have been confirmed to be associated with NIF or not (needs to be manually updated in DB), export the results in a format that can be uploaded into NIF CRM


Capturing Engagements from Calendar
-----------------------------------

Imports events exported from Mac Outlook calendar into a spreadsheet so
they can be filtered and uploaded into the NIF reporting tool.

To export events make sure you are using the old version of Mac Outlook and
go to File > Export and select "calendar" items to export. This will save a OLM
file, which you should provide as the input to the ``scripts/import_calendar.py``
script
