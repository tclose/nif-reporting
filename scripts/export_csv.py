"""
Search through publication content to search for likely terms
"""
import csv
from argparse import ArgumentParser
from app import app
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
    'Outcomes (including potential)', 'Status', 'Asset Type',
    '"Asset Type, if Other"', 'Data Asset Link', 'Is NIF Acknowledged?',
    '"If not, why"', 'Publication', 'Link to Software', 'Access Assigned',
    'Software Description', 'Advice Origin', '"Output type', ' if Other"',
    'Has Associated Project']

parser = ArgumentParser(__doc__)
parser.add_argument('output_csv', type=str, help="Path to output CSV")
args = parser.parse_args()


with app.app_context(), open(args.output_csv, 'w') as csv_f:

    csv_writer = csv.DictWriter(csv_f, CSV_HEADERS)

    csv_writer.writeheader()

    for pub in (Publication.query
                .filter_by(
                    nif_assoc=DEFINITE_NIF_ASSOC)
                .order_by(
                    Publication.date)).all():

        csv_writer.writerow({
            'Subject or Title': pub.title,
            'Fellow Named Author': 'FALSE',
            'Output Date': pub.date.strftime('%d/%m/%Y'),
            'Origin': 'Research Community',
            'Output Type': 'Publication',
            'Node Contact': 'Prof. Fernando Calamante',
            'DOI or Link': 'http://dx.doi.org/' + pub.doi,
            'Is NIF Acknowledged?': 'No',
            '"If not, why"': 'Offsite instrument',
            'Publication': pub.pub_name,
            'Has Associated Project': 'No'})
