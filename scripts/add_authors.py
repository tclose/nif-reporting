"""
Script to find Scopus records corresponding to list of authors
"""
import pybliometrics.scopus as sc
from app import app, db
from app.models import Researcher


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

    db.session.add(Researcher(
        first,
        last,
        initials=initials,
        scopus_ids=[a.eid for a in authors]))
    db.session.commit()
