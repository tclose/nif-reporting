#!/usr/bin/env python3

import typing as ty
import scholarly.author_parser
from argparse import ArgumentParser
from datetime import datetime
import attrs
import csv
from scholarly import scholarly


@attrs.define
class Author:
    first_name: str
    last_name: str
    initials: str
    google_id: str

    @property
    def name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def query(self):
        return f"{self.first_name} {self.last_name}"


CSV_HEADERS = ['NIF Supported (Y/N)', 'URL',
               'Year', 'Authors', 'Journal', 'Title']

AUTHORS = [
    # Author("Glenda", "Halliday", "G.M.", "WkE9CXgAAAAJ"),
    # Author("Olivier", "Piguet", None, "35Vz7wEAAAAJ"),
    Author("Paul", "Haber", None, "S-HMlCAAAAAJ"),
    Author("Ron", "Grunstein", None, "27ocvBwAAAAJ"),
    Author("Matthew", "Kiernan", None, "8ZJ9ZsUAAAAJ"),
    Author("Luke", "Henderson", "L.A.", "9SrabAMAAAAJ"),
    Author("Sharon", "Naismith", None, "xEwXhb0AAAAJ"),
    Author("Daniel", "Roquet", None, "AGQ5ZfcAAAAJ"),
    Author("Adam", "Guastella", None, "or_5_fMAAAAJ"),
    Author("Joel", "Pearson", None, "MqkRUgUAAAAJ"),
    Author("Shantel", "Duffy", None, "PoxEqngAAAAJ"),
    Author("Mark", "Onslow", None, None),
    Author("Amanda", "Salis", None, None),
    Author("Michael", "Barnett", None, "iZVWDzwAAAAJ"),
    Author("Simon", "Lewis", "S.J.G.", "FYneq_UAAAAJ"),
    Author("Ramon", "Landin-Romero", None, "9qD3uFAAAAAJ"),
    Author("Greg", "Kaplan", None, None),
    Author("James", "Shine", "J.M.", "Uxvu7CsAAAAJ"),
    Author("Ian", "Hickie", "I.B.", "5cRsn2AAAAAJ"),
    Author("Che", "Fornusek", None, None),
]


parser = ArgumentParser(__doc__)
parser.add_argument(
    "output_csv",
    type=str,
    help="the output CSV",
)
parser.add_argument(
    "--start-date",
    type=str,
    default=None,
    help="The year to search for (YYYY-MM-DD format)",
)
parser.add_argument(
    "--end-date",
    type=str,
    default=None,
    help="The year to search for (YYYY-MM-DD format)",
)
args = parser.parse_args()


def search_google_scholar(authors: ty.List[Author], start_date: str, end_date: str):
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.strptime(end_date, "%Y-%m-%d")
    pubs = []
    for author in authors:
        # if author.google_id:
        #     google_author = scholarly.search_author_id(author.google_id)
        # else:
        #     possible_authors = scholarly.search_author(author.query)
        #     google_author = next(possible_authors, None)
        author_pubs = list(scholarly.search_pubs(
            author.name, year_low=start_date.year, year_high=end_date.year
        ))
        print(
            f"Found {len(author_pubs)} publications for {author.name}"
        )
        for pub in author_pubs:
            if author.google_id and author.google_id not in pub["author_id"]:
                continue
            pubs.append(pub)
    return pubs


pubs = search_google_scholar(AUTHORS, args.start_date, args.end_date)

with open(args.output_csv, "w") as csv_f:
    csv_writer = csv.DictWriter(csv_f, CSV_HEADERS)

    csv_writer.writeheader()

    for pub in pubs:
        bib = pub["bib"]
        csv_writer.writerow({
            'URL': pub["pub_url"],
            'Year': bib.get("pub_year", ""),
            'Authors': ", ".join(a for a in bib["author"] if a),
            'Journal': bib.get("journal", ""),
            'Title': bib["title"]})

print(f"wrote collected publications to {args.output_csv}")
