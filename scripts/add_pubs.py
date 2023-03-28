#!/usr/bin/env python3
from datetime import datetime
from argparse import ArgumentParser
from sqlalchemy import orm, or_
import pybliometrics.scopus as sc
from app import app, db
from app.models import Researcher, Publication, ScopusAuthor


parser = ArgumentParser(__doc__)
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


DATE_FORMAT = "%Y-%m-%d"

if args.start_date:
    start_date = datetime.strptime(args.start_date, DATE_FORMAT)
else:
    start_date = datetime.time(year=1900)
if args.end_date:
    end_date = datetime.strptime(args.end_date, DATE_FORMAT)
else:
    end_date = datetime.today()

with app.app_context():
    for researcher in Researcher.query.all():
        for author in researcher.scopus_authors:
            search_str = f"au-id({author.scopus_id})"
            author_pubs = sc.ScopusSearch(search_str, timeout=3000).results
            print(f"Found {len(author_pubs)} publications in total for '{author.name}'")
            author_pubs_in_range = [
                p
                for p in author_pubs
                if (
                    datetime.strptime(p.coverDate, DATE_FORMAT) >= start_date
                    and datetime.strptime(p.coverDate, DATE_FORMAT) <= end_date
                )
            ]
            print(
                f"Found {len(author_pubs_in_range)} publications between {args.start_date} "
                f"and {args.end_date} for '{author.name}'"
            )
            for pub in author_pubs_in_range:
                scopus_id = pub.eid.split("-")[-1]
                if pub.doi:
                    pub_filter = or_(
                        Publication.scopus_id == scopus_id,
                        Publication.doi == pub.doi,
                    )
                else:
                    pub_filter = Publication.scopus_id == scopus_id
                publication = Publication.query.filter(pub_filter).one_or_none()
                if publication is None:
                    publication = Publication(
                        date=datetime.strptime(pub.coverDate, DATE_FORMAT).date(),
                        doi=pub.doi,
                        scopus_id=scopus_id,
                        pii=pub.pii,
                        title=pub.title,
                        pubmed_id=pub.pubmed_id,
                        volume=pub.volume,
                        pub_name=pub.publicationName,
                        openaccess=(pub.openaccess == "1"),
                        issue_id=pub.issueIdentifier,
                        abstract=pub.description,
                        issn=pub.issn,
                    )
                    for pub_author in pub.author_ids.split(";"):
                        try:
                            scopus_author = ScopusAuthor.query.filter_by(
                                scopus_id=int(pub_author)
                            ).one()
                        except orm.exc.NoResultFound:
                            pass
                        else:
                            publication.scopus_authors.append(scopus_author)
                    db.session.add(publication)
                    db.session.commit()
