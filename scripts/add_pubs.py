#!/usr/bin/env python3
from datetime import datetime
from argparse import ArgumentParser
from sqlalchemy import orm, or_
import pybliometrics.scopus as sc
from app import app, db
from app.models import Researcher, Publication, ScopusAuthor


parser = ArgumentParser(__doc__)
parser.add_argument('--year', type=int, default=None,
                    help="The year to search for")
args = parser.parse_args()

if args.year is None:
    year = datetime.today().year
else:
    year = args.year

DATE_FORMAT = '%Y-%m-%d'

with app.app_context():

    for researcher in Researcher.query.all():

        for author in researcher.scopus_authors:
            search_str = 'au-id({}) AND limit-to(pubyear, {})'.format(author.scopus_id,
                                                             year)
            author_pubs = sc.ScopusSearch(search_str, timeout=3000).results
            if author_pubs:
                num_pubs = len(author_pubs)
                print(f"Found {num_pubs} publications found for '{author.name}'")
                for pub in author_pubs:
                    scopus_id = pub.eid.split('-')[-1]
                    if pub.doi:
                        pub_filter = or_(Publication.scopus_id == scopus_id,
                                         Publication.doi == pub.doi)
                    else:
                        pub_filter = Publication.scopus_id == scopus_id
                    publication = Publication.query.filter(pub_filter).one_or_none()
                    if publication is None:
                        publication = Publication(
                            date=datetime.strptime(
                                pub.coverDate, DATE_FORMAT).date(),
                            doi=pub.doi,
                            scopus_id=scopus_id,
                            pii=pub.pii,
                            title=pub.title,
                            pubmed_id=pub.pubmed_id,
                            volume=pub.volume,
                            pub_name=pub.publicationName,
                            openaccess=(pub.openaccess == '1'),
                            issue_id=pub.issueIdentifier,
                            abstract=pub.description,
                            issn=pub.issn)
                        for pub_author in pub.author_ids.split(';'):
                            try:
                                scopus_author = ScopusAuthor.query.filter_by(
                                    scopus_id=int(pub_author)).one()
                            except orm.exc.NoResultFound:
                                pass
                            else:
                                publication.scopus_authors.append(
                                    scopus_author)
                        db.session.add(publication)
                        db.session.commit()
            else:
                print(f"WARNING! No publications found for '{author.name}'")
