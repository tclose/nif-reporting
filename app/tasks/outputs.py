import requests
import pybliometrics.scopus as sc
from app import app

BASE = "http://api.elsevier.com/"


app.config['API_KEY']

# request_params={'proxies': {"http": "web-cache-ext.usyd.edu.au:8080"}}

AUTHOR = BASE + 'content/author/author_id/26631575100'

FULL_TEXT = BASE + 'content/article/pii'

for author_id in ['26631575100']:
    pub_search = sc.ScopusSearch('AU-ID({})'.format(author_id))

    for pub in pub_search.results:
        if pub.pii:
            response = requests.get(
                FULL_TEXT + pub.pii,
                headers={
                    "X-ELS-APIKey"  : app.config['API_KEY'],
                    "Accept"        : 'application/json'})
            if response.ok:
                full_text = response['full-text-retrieval-response']
                print("Retrieved full text for {}".format(pub))
            else:
                print("\n\nCould not retrieve text for {}:\n{}".format(
                    pub, response.text))
        else:
            print("\n\nCould not retrieve text for {} as it is not on SD".format(
                pub))
        