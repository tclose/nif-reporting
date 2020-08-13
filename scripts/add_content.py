"""
Script to download full text articles for publications so they can be searced
for key terms
"""
import os.path
import json
import io
from urllib.parse import unquote as unquote_url
import requests
from requests.exceptions import ConnectionError
from PyPDF2 import PdfFileReader
from bs4 import BeautifulSoup
import pybliometrics.scopus as sc
from app import PKG_DIR, db
from app.models import Publication
from app.constants import (
    CANT_ACCESS_CONTENT, PLAIN_TEXT_ACCESS_CONTENT, HTML_ACCESS_CONTENT,
    PDF_ACCESS_CONTENT, UNKNOWN_ACCESS_CONTENT)



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

content_dir = os.path.join(PKG_DIR, 'publication-content')
os.makedirs(content_dir, exist_ok=True)

for pub in Publication.query.all():

    content_path = os.path.join(content_dir, pub.scopus_id + (
        '.txt' if pub.pii is not None else '.html'))

    if not os.path.exists(content_path):
        if pub.pii:
            content = content_from_pii(pub.pii)
            if content is None:
                pub.access_status = CANT_ACCESS_CONTENT
            else:
                pub.access_status = PLAIN_TEXT_ACCESS_CONTENT
        elif pub.doi:
            content = content_from_doi(pub.doi)
            if content is None:
                pub.access_status = CANT_ACCESS_CONTENT
            else:
                pub.access_status = HTML_ACCESS_CONTENT
        else:
            pub.access_status = UNKNOWN_ACCESS_CONTENT

        if content:
            with open(content_path, 'w') as f:
                f.write(str(content))
        db.session.commit()
