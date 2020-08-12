import requests
from urllib.parse import unquote as unquote_url
from bs4 import BeautifulSoup
import pybliometrics.scopus as sc

DOI_RESOLVER = 'http://doi.org/'

def text_from_doi(doi):
    html = BeautifulSoup(requests.get(DOI_RESOLVER + doi).text)
    redirect_url = unquote_url(html.find(id='redirectURL').attrs['value'])
    return requests.get(redirect_url).text

def text_from_pii(pii):

    return None

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
    print('Title: {} | PII: {} | DOI: {}'.format(pub.title, pub.pii, pub.doi))

