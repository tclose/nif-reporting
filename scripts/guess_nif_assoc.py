"""
Search through publication content to search for likely terms
"""
import os
import re
import csv
import logging
from argparse import ArgumentParser
from datetime import datetime
from app import app, db
from app.models import Publication
from app.constants import (
    POSSIBLE_NIF_ASSOC, UNLIKELY_NIF_ASSOC, UNKNOWN_ACCESS_CONTENT,
    PROBABLE_NIF_ASSOC)

mri_re = re.compile(
    r'(.{50}(?:MRI|(?:M|m)agnetic\s+(?:R|r)esonance\s+(?:I|i)maging).{50})')
ge_re = re.compile(
    r'(.{50}(?<!\w)(?:GE|G.E.|(?:G|g)eneral\s+(?:E|e)lectric)(?!\w).{50})')

CSV_HEADERS = ['NIF Supported (Y/N)', 'Likelihood', 'Scopus ID', 'DOI',
               'Date', 'Authors', 'Journal', 'Title']

parser = ArgumentParser(__doc__)
parser.add_argument('output_csv', type=str, help="Path to output CSV")
parser.add_argument(
    'start_date', type=str,
    help="The start date to list publications from in d/m/y format")
parser.add_argument(
    'end_date', type=str,
    help="The end date to list publications until in d/m/y format")
parser.add_argument('--possible_log', type=str, default=None,
                    help="Location of log file to output possible matches")
parser.add_argument('--probable_log', type=str, default=None,
                    help="Location of log file to output probable matches")
args = parser.parse_args()

probable_logger = logging.getLogger('nrt_probable')
possible_logger = logging.getLogger('nrt_possible')
other_logger = logging.getLogger('nrt_other')

formatter = logging.Formatter('%(message)s')

start_date = datetime.strptime(args.start_date, '%d/%m/%y')
end_date = datetime.strptime(args.end_date, '%d/%m/%y')

if args.possible_log:
    os.remove(args.possible_log)
    possible_logger.setLevel(logging.INFO)
    handler = logging.FileHandler(args.possible_log)
    handler.setFormatter(formatter)
    possible_logger.addHandler(handler)

if args.probable_log:
    os.remove(args.probable_log)
    probable_logger.setLevel(logging.INFO)
    handler = logging.FileHandler(args.probable_log)
    handler.setFormatter(formatter)
    probable_logger.addHandler(handler)

with app.app_context(), open(args.output_csv, 'w') as csv_f:

    csv_writer = csv.DictWriter(csv_f, CSV_HEADERS)

    csv_writer.writeheader()

    query = (Publication.query
             .filter(
                Publication.date >= start_date,
                Publication.date <= end_date))

    for pub in query.all():
        if pub.has_content:
            mri_matches = mri_re.findall(pub.content)
            if mri_matches:
                ge_matches = ge_re.findall(pub.content)
                if ge_matches:
                    pub.nif_assoc = PROBABLE_NIF_ASSOC
                    probable_logger.info(
                        ('%s: %s - PROBABLE:\n'
                         '  --- MRI ---\n    %s\n  --- GE ---\n    %s\n'),
                        pub.scopus_id,
                        pub.title,
                        '\n    '.join(mri_matches),
                        '\n    '.join(ge_matches))
                else:
                    pub.nif_assoc = POSSIBLE_NIF_ASSOC
                    possible_logger.info(
                        '%s: %s - POSSIBLE:\n    %s\n',
                        pub.scopus_id,
                        pub.title,
                        '\n    '.join(mri_matches))
            else:
                pub.nif_assoc = UNLIKELY_NIF_ASSOC
                other_logger.info(
                    '%s: %s - UNLIKELY',
                    pub.scopus_id,
                    pub.title)
        else:
            pub.nif_assoc = UNKNOWN_ACCESS_CONTENT
            other_logger.info(
                '%s: %s - UNKNOWN',
                pub.scopus_id,
                pub.title)
        db.session.commit()

    for pub in query.order_by(
            Publication.nif_assoc.desc(),
            Publication.date):
        csv_writer.writerow({
            'Scopus ID': pub.scopus_id,
            'DOI': ('https://dx.doi.org/' + pub.doi if pub.doi else ''),
            'Date': pub.date.strftime('%Y-%m-%d'),
            'Likelihood': pub.nif_assoc_str,
            'Authors': '; '.join(r.name for r in pub.researchers_involved),
            'Journal': pub.pub_name,
            'Title': pub.title})
