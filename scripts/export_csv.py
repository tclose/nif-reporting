"""
Search through publication content to search for likely terms
"""
import csv
from argparse import ArgumentParser
from datetime import datetime
from app import app
from app.models import Publication
from app.constants import DEFINITE_NIF_ASSOC, NIF_ASSOC


# OUTPUT_CSV_HEADERS = [
#     'Subject or Title', 'Outputs Owner', 'Outputs Owner ID', 'Created Time',
#     'Modified Time', 'Last Activity Time', 'Tag', 'Fellow Named Author',
#     'Output Date', 'Origin', 'Output Type', 'Node Contact', 'DOI or Link',
#     'Advice Provided', 'Government Priority', 'Output summary',
#     'IP or Commercialisation Activity', 'Granting Body',
#     'Link for further info', 'Duration (years)', 'Funding Amount',
#     'Announcement Link', 'File Number', 'Link', 'Audience',
#     'Outcomes (including potential)', 'Status', 'Asset Type',
#     '"Asset Type, if Other"', 'Data Asset Link', 'Is NIF Acknowledged?',
#     '"If not, why"', 'Publication', 'Link to Software', 'Access Assigned',
#     'Software Description', 'Advice Origin', '"Output type', ' if Other"',
#     'Has Associated Project']

# NEW_OUTPUT_CSV_HEADERS  = [
#     'Subject or Title', 'Outputs Owner', 'Outputs Owner ID', 'Created Time',
#     'Modified Time', 'Last Activity Time', 'Tag', 'Fellow Named Author',
#     'Output Date', 'Origin', 'Output Type', 'Node Contact', 'DOI or Link',
#     'Advice Provided', 'Government Priority', 'Output summary',
#     'IP or Commercialisation Activity', 'Granting Body',
#     'Link for further info', 'Duration (years)', 'Funding Amount',
#     'Announcement Link', 'File Number', 'Link', 'Audience',
#     'Outcomes (including potential)', 'Status', 'Asset Type',
#     'Asset Type, if Other', 'Data Asset Link', 'Is NIF Acknowledged?',
#     'If not, why', 'Publication', 'Link to Software', 'Access Assigned',
#     'Software Description', 'Advice Origin', 'Output type, if Other',
#     'Has Associated Project', 'Unsubscribed Mode', 'Unsubscribed Time']

OUTPUT_CSV_HEADERS = [
    'Subject or Title', 'Output Date', 'DOI or Link', 'Publication',
    'Fellow Named Author', 'Origin', 'Output Type', 'Node Contact',
    'Is NIF Acknowledged?', 'If not, why', 'Has Associated Project']


parser = ArgumentParser(__doc__)
parser.add_argument('output_csv', type=str, help="Path to output CSV")
parser.add_argument(
    'start_date', type=str,
    help="The start date to list publications from in d/m/y format")
parser.add_argument(
    'end_date', type=str,
    help="The end date to list publications until in d/m/y format")
args = parser.parse_args()

start_date = datetime.strptime(args.start_date, '%d/%m/%y')
end_date = datetime.strptime(args.end_date, '%d/%m/%y')

with app.app_context(), open(args.output_csv, 'w') as csv_f:

    csv_writer = csv.DictWriter(csv_f, OUTPUT_CSV_HEADERS)

    csv_writer.writeheader()

    query = (Publication.query
             .filter(
                 Publication.nif_assoc == DEFINITE_NIF_ASSOC,
                 Publication.date >= start_date,
                 Publication.date <= end_date)
             .order_by(Publication.date))

    for pub in query.all():
        row = {
            'Subject or Title': pub.title,
            'Output Date': pub.date.strftime('%d/%m/%Y'),
            'DOI or Link': 'http://dx.doi.org/' + pub.doi,
            'Publication': pub.pub_name,
            'Fellow Named Author': 'FALSE',
            'Origin': 'Research Community',
            'Output Type': 'Publication',
            'Node Contact': 'Prof. Fernando Calamante',
            'Is NIF Acknowledged?': 'No',
            'If not, why': 'Offsite instrument',
            'Has Associated Project': 'No'}
        csv_writer.writerow(row)
