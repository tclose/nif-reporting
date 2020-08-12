from argparse import ArgumentParser
import requests
import pybliometrics.scopus as sc

BASE = "http://api.elsevier.com/"

# request_params={'proxies': {"http": "web-cache-ext.usyd.edu.au:8080"}}

AUTHOR = BASE + 'content/author/author_id/26631575100'
FULL_TEXT = BASE + 'content/article/pii'

parser = ArgumentParser()
args = parser.parse_args()



for author_id in ['26631575100']:
    pub_search = sc.ScopusSearch('AU-ID({})'.format(author_id))

    for pub in pub_search.results:
        if pub.pii:
            response = requests.get(
                FULL_TEXT + pub.pii,
                headers={
                    "X-ELS-APIKey"  : sc.config['Authentication']['APIKey'],
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
        