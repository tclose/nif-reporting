from datetime import datetime
from argparse import ArgumentParser
import pybliometrics.scopus as sc
from app import app, db
from app.models import Researcher, Publication


parser = ArgumentParser(__doc__)
parser.add_argument('--year', type=int, default=None,
                    help="The year to search for")
args = parser.parse_args()

DATE_FORMAT = '%Y-%m-%d'

with app.app_context():

    for researcher in Researcher.query.all():

        for author in researcher.scopus_authors:
            search_str = 'au-id({}) AND pubyear = 2020'.format(
                author.scopus_id.split('-')[-1])
            author_pubs = sc.ScopusSearch(search_str).results
            if author_pubs:
                for pub in author_pubs:
                    db.session.add(Publication(
                        date=datetime.strptime(
                            pub.coverDate, DATE_FORMAT).date(),
                        doi=pub.doi,
                        eid=pub.eid,
                        pii=pub.pii,
                        title=pub.title,
                        pubmed_id=pub.pubmed_id,
                        volume=pub.volume,
                        pub_name=pub.publicationName,
                        openaccess=(pub.openaccess == '1'),
                        issue_id=pub.issueIdentifier,
                        issn=pub.issn))
                    db.session.commit()
