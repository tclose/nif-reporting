from copy import copy
import json
from elsapy.elsclient import ElsClient
from elsapy.elsprofile import ElsAuthor
from elsapy.elsdoc import FullDoc
import requests

base_uri = "https://api.elsevier.com/"
usyd_proxies = {"http": "web-cache-ext.usyd.edu.au:8080"}

with open('./config.json') as f:
    config = json.load(f)


client = ElsClient(config['apiKey'])

me = ElsAuthor()

author_search_path = "content/search/author?"

s = requests.Session()

def get(path, **kwargs):
    """Gets path inserting base Scopus API URI and Usyd proxies

    Args:
        path (str): sub-path to API endpoint

    Keyword arguments are passed to requests.Session.get as query string
    parameters
    """
    params = copy(kwargs)
    params['apiKey'] = api_key
    resp = s.get(base_uri + path, proxies=usyd_proxies, params=params)
    if not resp.ok:
        raise Exception("Get request '{}' returned an error '{}'".format(
            resp.url, resp.status_code))
    return resp


response = get(author_search_path, query='au-id%28{}'.format(26631575100))

print(response.status_code)
print(response.url)
