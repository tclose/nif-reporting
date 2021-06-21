#!/usr/bin/env python3
"""
Script to download full text articles linked to facility researchers and
search for references to NIF-related instruments
"""
import os.path
import json
import io
from argparse import ArgumentParser
from urllib.parse import unquote as unquote_url
import requests
from requests.exceptions import ConnectionError
from PyPDF2 import PdfFileReader
from bs4 import BeautifulSoup
import pybliometrics.scopus as sc

DOI_RESOLVER = 'http://doi.org/'
SCIENCE_DIRECT = 'http://api.elsevier.com/content/article/pii/'
CROSSREF = 'https://api.wiley.com/onlinelibrary/tdm/v1/articles/'

crossref_config = os.path.join(os.environ['HOME'], '.crossref', 'config.json')

if os.path.exists(crossref_config):
    with open(crossref_config) as f:
        crossref_token = json.load(f)['APIToken']


def content_from_doi(doi):
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
    if html.find('title').text.startswith('Attention Required!'):
        return None
        # return content_from_crossref(doi)
    return html

def content_from_crossref(doi):
    response = requests.get(
        CROSSREF + doi,
        headers={"CR-Clickthrough-Client-Token"  : crossref_token,
                 "Accept"        : 'application/pdf'})
    pdf = PdfFileReader(io.BytesIO(response.content))
    text = ''
    for page in pdf.pages:
        text += page.extractText()
    return text

def content_from_pii(pii):
    response = requests.get(
        SCIENCE_DIRECT + pii,
        headers={"X-ELS-APIKey"  : sc.config['Authentication']['APIKey'],
                 "Accept"        : 'application/json'})
    text = None
    if response.ok:
        try:
            text = response.json()[
                'full-text-retrieval-response']['originalText']
        except KeyError:
            pass
    return text


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
parser.add_argument('--content_cache', default=None,
                    help="Directory to dump full text outputs")
args = parser.parse_args()

if args.content_cache:
    os.makedirs(args.content_cache, exist_ok=True)

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

if args.content_cache:
    fnames = os.listdir(args.content_cache)
    cache = {n.split(':')[0]: n for n in fnames}
else:
    cache = None

for pub in publications:

    content = None
    try:
        fpath = os.path.join(args.content_cache, cache[pub.eid])
    except KeyError:
        fpath = os.path.join(
            args.content_dir,
            pub.eid + ':'
            + pub.title[:80].replace('/', '_').replace('\\', '_'))
        if pub.pii:
            content = content_from_pii(pub.pii)
            if content is None:
                status = "Could not access PII ({}{})".format(SCIENCE_DIRECT,
                                                              pub.pii)
            else:
                status = 'Text downloaded from PII'
                fpath += '.txt'
        elif pub.doi:
            content = content_from_doi(pub.doi)
            if content is None:
                status = "Could not access DOI"
            else:
                status = "Downloaded from DOI"
                fpath += 'html'
        else:
            status = "Could not find DOI or PII for title!!!"

        if content and args.content_dir:
            with open(fpath, 'w') as f:
                f.write(str(content))
        print(('ID: {} | Title: {} | '
               'PII: http://api.elsevier.com/content/article/pii/{} | '
               'DOI: http://dx.doi.org/{} | Status: {}\n').format(
                   pub.eid, pub.title, pub.pii, pub.doi, status))
    else:
        with open(fpath) as f:
            content = f.read()
        print('ID: {} | Title: {} | Status: from cache'
              .format(pub.eid, pub.title))

