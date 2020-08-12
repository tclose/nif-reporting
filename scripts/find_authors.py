import sys
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
    text = None
    if response.ok:
        try:
            text =  response.json()['full-text-retrieval-response']['originalText']
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
    print('Title: {} | PII: {} | DOI: {}\n'.format(pub.title, pub.pii, pub.doi))
    if pub.pii:
        full_text = text_from_pii(pub.pii)
        if full_text is None:
            full_text = "Could not access PII ({}{})".format(
                    SCIENCE_DIRECT, pub.pii)
    elif pub.doi:
        full_text = text_from_doi(pub.doi)
        if full_text is None:
            full_text = "Could not access DOI ({})".format(pub.doi)
        else:
            full_text = 'http://doi.org/' + pub.doi
    else:
        full_text = "Could not find DOI or PII for title!!!"
        
    print(str(full_text) + '\n\n=============================================\n\n')
