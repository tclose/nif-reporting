"""
Database models for monitoring researcher who have used the facility and their
outputs
"""
from app import db


class Researcher(db.Model):
    """
    A researcher who has used the facility
    """

    __tablename__ = 'researchers'

    id = db.Column(db.Integer, primary_key=True)
    given_name = db.Column(db.String(100))
    surname = db.Column(db.String(200))
    initials = db.Column(db.String(50))
    orcid = db.Column(db.String(200))
    title = db.Column(db.String(20))

    _scopus_ids = db.relationship('ScopusAuthor', backref='researcher')

    def __init__(self, given_name, surname, initials=None, scopus_ids=None,
                 orcid=None, title=None):
        self.given_name = given_name
        self.surname = surname
        self.initials = initials
        self.scopus_ids = scopus_ids
        self.orcid = orcid
        self.title = title

    @property
    def name(self):
        name = '{} {}'.format(self.given_name, self.surname)
        if self.title is not None:
            name = '{} ' + name
        return name

    @property
    def scopus_ids(self):
        return [i.scopus_id for i in self._scopus_ids]

    @scopus_ids.setter
    def scopus_ids(self, ids):
        scopus_ids = []
        for id in ids:
            scopus_ids.append(ScopusAuthor(self, id))
        self._scopus_ids = scopus_ids

    def __str__(self):
        return self.name


class Publication(db.Model):

    __tablename__ = 'publications'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date)
    doi = db.Column(db.String(200))
    eid = db.Column(db.String(100))
    pii = db.Column(db.String(100))
    title = db.Column(db.String(500))
    pubmed_id = db.Column(db.String(100))
    volume = db.Column(db.String(100))
    pub_name = db.Column(db.String(200))
    openaccess = db.Column(db.Boolean)
    issue_id = db.Column(db.String(100))
    issn = db.Column(db.String(100))

    author_ids = db.relationship(db.Column(db.String(100)))

    def __init__(self, doi, title, eid=None, pii=None, date=None,
                 pubmed_id=None, volume=None, pub_name=None, openaccess=None,
                 issue_id=None, issn=None, author_ids=()):    
        self.date = date
        self.doi = doi
        self.eid = eid
        self.pii = pii
        self.title = title
        self.pubmed_id = pubmed_id
        self.volume = volume
        self.pub_name = pub_name
        self.openaccess = openaccess
        self.issue_id = issue_id
        self.issn = issn
        self.author_ids = author_ids


class Affiliation(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    scopus_id = db.Column(db.String(200), unique=True)


class ScopusAuthor(db.Model):

    __tablename__ = 'scopusauthors'

    id = db.Column(db.Integer, primary_key=True)
    researcher_id = db.Column(db.Integer,
                              db.ForeignKey(
                                  'researchers.id',
                                  name='fk_scopusauthors_researchers'))
    scopus_id = db.Column(db.String(200), unique=True)
    affiliation_id = db.Column(db.Integer,
                               db.ForeignKey(
                                   'affiliations.id',
                                   name='fk_scopusauthors_affiliations'))

    affiliation = db.relationship('Affiliation', backref='authors')

    def __init__(self, researcher, scopus_id, affiliation=None):
        self.researcher = researcher
        self.scopus_id = scopus_id
        self.affiliation = affiliation
