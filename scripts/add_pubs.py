from argparse import ArgumentParser
import pybliometrics.scopus as sc
from app import app, db
from app.models import Researcher, Publication


parser = ArgumentParser(__doc__)
parser.add_argument('--year', type=int, default=None,
                    help="The year to search for")
args = parser.parse_args()


with app.app_context():

    for researcher in Researcher.query.all():

        for author in researcher.scopus_authors:
            search_str = 'au-id({}) AND pubyear = 2020'.format(
                author.eid.split('-')[-1])
            author_pubs = sc.ScopusSearch(search_str).results
            if author_pubs:
                for pub in author_pubs:
                    db.session.add(Publication(
                        date=pub.coverDate,
                        doi=pub.doi,
                        eid=pub.eid,
                        pii=pub.pii,
                        title=pub.title,
                        pubmed_id=pub.pubmed_id,
                        issue_id=pub.issueIdentifier,
                        volume=pub.volume,
                        pub_name=pub.publicationName,
                        openaccess=pub.openaccess,
                        issn=pub.issn,
                        abstract=pub.abstract))
