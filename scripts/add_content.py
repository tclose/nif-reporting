#!/usr/bin/env python3
"""
Script to download full text articles for publications so they can be searced
for key terms
"""
import os.path
import json
import logging
import re
import io
from fuzzywuzzy import fuzz
from argparse import ArgumentParser
from urllib.parse import unquote as unquote_url
import requests
from requests.exceptions import ConnectionError
from PyPDF2 import PdfFileReader
from bs4 import BeautifulSoup
import pybliometrics.scopus as sc
from app import db
from app.models import Publication
from app.constants import (
    CANT_ACCESS_CONTENT, PLAIN_TEXT_ACCESS_CONTENT, HTML_ACCESS_CONTENT,
    UNKNOWN_ACCESS_CONTENT)  # PDF_ACCESS_CONTENT, 


logging.basicConfig()

parser = ArgumentParser(__doc__)
parser.add_argument(
    '--new', action='store_true', default=False,
    help="Only attempt to get content for publications that are new ")
args = parser.parse_args()

DOI_RESOLVER = 'http://doi.org/'
SCIENCE_DIRECT = 'http://api.elsevier.com/content/article/pii/'
CROSSREF = 'https://api.wiley.com/onlinelibrary/tdm/v1/articles/'

crossref_config = os.path.join(os.environ['HOME'], '.crossref', 'config.json')

USER_AGENT_HEADER = {
    'User-Agent': ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) '
                   'AppleWebKit/537.36 (KHTML, like Gecko) '
                   'Chrome/50.0.2661.102 Safari/537.36')}

if os.path.exists(crossref_config):
    with open(crossref_config) as f:
        crossref_token = json.load(f)['APIToken']


def content_from_doi(doi, pub):
    try:
        response = requests.get(DOI_RESOLVER + doi, headers=USER_AGENT_HEADER)
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
    if not html.find(text=lambda s: fuzz.ratio(pub.title, s.strip()) > 60):
        #     or not html.body.find(text=re.compile('.*methods.*', flags=re.IGNORECASE))):
        # with open('/Users/tclose/Desktop/doi-content.html', 'w') as f:
        #     f.write(response.text)
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


for pub in Publication.query.all():
    if not pub.has_content and (not args.new or pub.access_status is None):
        if pub.pii:
            content = content_from_pii(pub.pii)
            if content is None:
                pub.access_status = CANT_ACCESS_CONTENT
            else:
                pub.access_status = PLAIN_TEXT_ACCESS_CONTENT
        elif pub.doi:
            content = content_from_doi(pub.doi, pub)
            if content is None:
                pub.access_status = CANT_ACCESS_CONTENT
            else:
                pub.access_status = HTML_ACCESS_CONTENT
        else:
            pub.access_status = UNKNOWN_ACCESS_CONTENT

        # if content:
            # pub.content = content
        db.session.commit()
        if pub.access_status in (1, 2):
            status = "Successfully"
        elif pub.access_status == 0:
            status = "Unsuccessfully"
        elif pub.access_status == -1:
            status = "No method for"
        logging.info(f"{status} accessed content for {pub.id} ({pub.scopus_id}")
