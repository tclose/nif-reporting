from datetime import datetime
from argparse import ArgumentParser
from sqlalchemy import orm
import pybliometrics.scopus as sc
from app import app, db
from app.models import Researcher, Publication, ScopusAuthor


parser = ArgumentParser(__doc__)
parser.add_argument('--year', type=int, default=None,
                    help="The year to search for")
args = parser.parse_args()

DATE_FORMAT = '%Y-%m-%d'

with app.app_context():

    for researcher in Researcher.query.all():

        for author in researcher.scopus_authors:
            search_str = 'au-id({}) AND pubyear = 2020'.format(author.scopus_id)
            author_pubs = sc.ScopusSearch(search_str).results
            if author_pubs:
                for pub in author_pubs:
                    publication = Publication.query.filter_by(eid=pub.eid).one_or_none()
                    if publication is None:
                        publication = Publication(
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
                            abstract=pub.description,
                            issn=pub.issn)
                        for pub_author in pub.author_ids.split(';'):
                            try:
                                scopus_author = ScopusAuthor.query.filter_by(
                                    scopus_id=int(pub_author)).one()
                            except orm.exc.NoResultFound:
                                pass
                            else:
                                publication.scopus_authors.append(scopus_author)
                        db.session.add(publication)
                        db.session.commit()

