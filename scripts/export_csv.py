"""
Search through publication content to search for likely terms
"""
import os
import re
import csv
import logging
from argparse import ArgumentParser
from app import app, db
from app.models import Publication
from app.constants import DEFINITE_NIF_ASSOC


CSV_HEADERS = [
    'Subject or Title', 'Outputs Owner', 'Outputs Owner ID', 'Created Time',
    'Modified Time', 'Last Activity Time', 'Tag', 'Fellow Named Author',
    'Output Date', 'Origin', 'Output Type', 'Node Contact', 'DOI or Link',
    'Advice Provided', 'Government Priority', 'Output summary',
    'IP or Commercialisation Activity', 'Granting Body',
    'Link for further info', 'Duration (years)', 'Funding Amount',
    'Announcement Link', 'File Number', 'Link', 'Audience',
    'Outcomes (including potential)', 'Status', 'Asset Type', '"Asset Type',
    ' if Other"', 'Data Asset Link', 'Is NIF Acknowledged?', '"If not',
    ' why"', 'Publication', 'Link to Software', 'Access Assigned',
    'Software Description', 'Advice Origin', '"Output type', ' if Other"',
    'Has Associated Project']

parser = ArgumentParser(__doc__)
parser.add_argument('output_csv', type=str, help="Path to output CSV")
args = parser.parse_args()


with app.app_context(), open(args.output_csv, 'w') as csv_f:
    
    csv_writer = csv.DictWriter(csv_f, CSV_HEADERS)

    csv_writer.writeheader()

    for pub in Publication.query.filter_by(
            Publication.nif_assoc == DEFINITE_NIF_ASSOC).all():

        csv_writer.writerow({
            'Subject or Title': pub.title,
            'Outputs Owner': pub.,
            'Outputs Owner ID': pub.,
            'Created Time': pub.,
            'Modified Time': pub.,
            'Last Activity Time': pub.,
            'Tag': pub.,
            'Fellow Named Author': pub.,
            'Output Date': pub.,
            'Origin': pub.,
            'Output Type': pub.,
            'Node Contact': pub.,
            'DOI or Link': pub.,
            'Advice Provided': pub.,
            'Government Priority': pub.,
            'Output summary': pub.,
            'IP or Commercialisation Activity': pub.,
            'Granting Body': pub.,
            'Link for further info': pub.,
            'Duration (years)': pub.,
            'Funding Amount': pub.,
            'Announcement Link': pub.,
            'File Number': pub.,
            'Link': pub.,
            'Audience': pub.,
            'Outcomes (including potential)': pub.,
            'Status': pub.,
            'Asset Type': pub.,
            '"Asset Type': pub.,
            ' if Other"': pub.,
            'Data Asset Link': pub.,
            'Is NIF Acknowledged?': pub.,
            '"If not': pub.,
            ' why"': pub.,
            'Publication': pub.,
            'Link to Software': pub.,
            'Access Assigned': pub.,
            'Software Description': pub.,
            'Advice Origin': pub.,
            '"Output type': pub.,
            ' if Other"': pub.,
            'Has Associated Project'
        })