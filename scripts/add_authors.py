"""
Script to find Scopus records corresponding to list of authors
"""
import os.path
import pybliometrics.scopus as sc
from sqlalchemy import orm
from app import app, db
from app.models import Researcher, ScopusAuthor, Affiliation


AUTHORS = [
    ('Glenda', 'Halliday', None),
    ('Olivier', 'Piguet', None),
    ('Paul', 'Haber', None),
    ('Ron', 'Grunstein', None),
    ('Matthew', 'Kiernan', None),
    ('Luke', 'Henderson', 'L.A.'),
    ('Sharon', 'Naismith', None),
    ('Daniel', 'Roquet', None),
    ('Adam', 'Guastella', None),
    ('Joel', 'Pearson', None),
    ('Shantel', 'Duffy', None),
    ('Mark', 'Onslow', None),
    ('Amanda', 'Salis', None),
    ('Michael', 'Barnett', None),
    ('Simon', 'Lewis', 'S.J.G.')]

VALID_AREAS = [
    'MEDI',
    'NEUR',
    'BIOC',
    'PSYC']

with app.app_context():

    if not os.path.exists(app.config['SQLALCHEMY_DATABASE_URI']):
        db.create_all()

    for first, last, initials in AUTHORS:
        all_authors = set(
            a for a in sc.AuthorSearch("authfirst({}) and authlast({})"
                                       .format(first, last)).authors
            if a.givenname.startswith(first))
        all_authors |= set(
            a for a in sc.AuthorSearch("authfirst({}.) and authlast({})"
                                       .format(first[0], last)).authors
            if a.givenname.startswith(first[0] + '.')
            or a.givenname.startswith(first))
        authors = [a for a in all_authors if a.city == 'Sydney']
        if not authors:
            authors = [a for a in all_authors if a.country == 'Australia']
        authors = [
            a for a in authors
            if (any(r in a.areas for r in VALID_AREAS) or a.areas == ' ()')
            and (a.surname.startswith(last) or last not in a.surname)]
        if initials:
            authors = [a for a in authors if initials == a.initials]

        researcher = Researcher(
            first,
            last,
            initials=initials)
        db.session.add(researcher)
        for author in authors:
            try:
                affiliation = Affiliation.query.filter_by(
                    scopus_id=author.affiliation_id).one()
            except orm.exc.NoResultFound:
                affiliation = Affiliation(
                    author.affiliation_id, author.affiliation, author.city,
                    author.country)
            scopus_author = ScopusAuthor(
                int(author.eid.split('-')[-1]),
                givenname=author.givenname,
                surname=author.surname,
                researcher=researcher,
                affiliation=affiliation,
                areas=author.areas)
            researcher.scopus_authors.append(scopus_author)

        db.session.commit()
