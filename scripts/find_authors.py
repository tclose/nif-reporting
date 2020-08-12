"""
Script to download full text articles linked to facility researchers and
search for references to NIF-related instruments
"""
import os.path as op
from argparse import ArgumentParser
from urllib.parse import unquote as unquote_url
import requests
from requests.exceptions import ConnectionError
from bs4 import BeautifulSoup
import pybliometrics.scopus as sc

DOI_RESOLVER = 'http://doi.org/'
SCIENCE_DIRECT = 'http://api.elsevier.com/content/article/pii/'


def text_from_doi(doi):
    try:
        response = requests.get(DOI_RESOLVER + doi)
    except ConnectionError:
        return None
    html = BeautifulSoup(response.text, features='lxml')
    redirect_tag = html.find(id='redirectURL')
    if redirect_tag:
        redirect_url = unquote_url(redirect_tag.attrs['value'])
        html = BeautifulSoup(requests.get(redirect_url).text,
                             features='lxml')
    return html

def text_from_pii(pii):
    response = requests.get(
        SCIENCE_DIRECT + pii,
        headers={"X-ELS-APIKey"  : sc.config['Authentication']['APIKey'],
                 "Accept"        : 'application/json'})
    return response.json()['full-text-retrieval-response']


AUTHORS = [
    ('Glenda', 'Halliday', None),
    ('Olivier', 'Piguet', None),
    ('Paul', 'Haber', None),
    ('Ron', 'Grunstein', None),
    ('Matthew', 'Kiernan', None),
    ('Luke', 'Henderson', 'L.A.'),
    ('Sharon', 'Naismith', None),
    ('Daniel', 'Roquet', None),
    ('Adam', 'Guastella', None),
    ('Joel', 'Pearson', None),
    ('Shantel', 'Duffy', None),
    ('Mark', 'Onslow', None),
    ('Amanda', 'Salis', None),
    ('Michael', 'Barnett', None),
    ('Simon', 'Lewis', 'S.J.G.')]

VALID_AREAS = [
    'MEDI',
    'NEUR',
    'BIOC',
    'PSYC']

parser = ArgumentParser(__doc__)
parser.add_argument('--full_text_dir', default=None,
                    help="Directory to dump full text outputs")
args = parser.parse_args()

if args.full_text_dir:
    os.makedirs(args.full_text_dir, exist_ok=True)

publications = []

for first, last, initials in AUTHORS:
    all_authors = set(
        a for a in sc.AuthorSearch("authfirst({}) and authlast({})"
                                   .format(first, last)).authors
        if a.givenname.startswith(first))
    all_authors |= set(
        a for a in sc.AuthorSearch("authfirst({}.) and authlast({})"
                                   .format(first[0], last)).authors
        if a.givenname.startswith(first[0] + '.')
        or a.givenname.startswith(first))
    authors = [a for a in all_authors if a.city == 'Sydney']
    if not authors:
        authors = [a for a in all_authors if a.country == 'Australia']
    authors = [a for a in authors
               if (any(r in a.areas for r in VALID_AREAS) or a.areas == ' ()')
               and (a.surname.startswith(last) or last not in a.surname)]
    if initials:
        authors = [a for a in authors if initials == a.initials]

    for author in authors:
        search_str = 'au-id({}) AND pubyear = 2020'.format(
            author.eid.split('-')[-1])
        author_pubs = sc.ScopusSearch(search_str).results
        if author_pubs:
            publications += author_pubs

print('Found {} publications, {} with PIIs, {} with DOIs:\n'.format(
    len(publications),
    len([p for p in publications if p.pii]),
    len([p for p in publications if p.doi])))

for pub in publications:

    full_text = None
    pii_text = None
    if pub.pii:
        full_text = text_from_pii(pub.pii)
        if full_text is None:
            status = 'Could not download from PII'
        else:
            status = 'Text downloaded from PII'
    if pub.doi:
        if full_text is not None:
            pii_text = full_text
        full_text = text_from_doi(pub.doi)
        if full_text is None:
            status = "Could not access DOI"
        else:
            status = "Downloaded from DOI"
    elif not pii_text:
        status = "Could not find DOI or PII for title!!!"

    if full_text and args.full_text_dir:
        with open(op.join(args.full_text_dir, pub.title[:100]) + '.html') as f:
            f.write(full_text)
        if pii_text:
            with open(op.join(args.full_text_dir, pub.title[:100])
                      + '.txt') as f:
                f.write(pii_text)

    print('Title: {} | PII: {} | DOI: {} | Status: {}\n'
          .format(pub.title, pub.pii, pub.doi, status))
