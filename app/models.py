"""
Database models for monitoring researchers who have used the facility and their
outputs
"""
import os.path
from sqlalchemy import orm
from app import db, PKG_DIR
from app.exceptions import NifReportingException


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

    _scopus_authors = db.relationship('ScopusAuthor', backref='researcher')

    def __init__(self, given_name, surname, initials=None, scopus_authors=(),
                 orcid=None, title=None):
        self.given_name = given_name
        self.surname = surname
        self.initials = initials
        self.scopus_authors = list(scopus_authors)
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
        return [i.scopus_id for i in self.scopus_authors]

    @property
    def scopus_authors(self):
        return self._scopus_authors

    @scopus_authors.setter
    def scopus_authors(self, authors):
        for author in authors:
            if author.researcher is None:
                author.researcher = self
            elif author.researcher is not self:
                raise NifReportingException(
                    "Mismatching researcher in scopus authors {}: {}".format(
                        self, author.researcher))
        self._scopus_authors = authors

    def __str__(self):
        return self.name


class Publication(db.Model):

    __tablename__ = 'publications'

    CONTENT_DIR = os.path.join(PKG_DIR, 'publication-content')

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date)
    scopus_id = db.Column(db.String(100), unique=True)
    doi = db.Column(db.String(200), unique=True)
    pii = db.Column(db.String(100), unique=True)
    title = db.Column(db.String(500))
    pubmed_id = db.Column(db.String(100), unique=True)
    volume = db.Column(db.String(100))
    pub_name = db.Column(db.String(200))
    openaccess = db.Column(db.Boolean)
    issue_id = db.Column(db.String(100))
    issn = db.Column(db.String(100))
    nif_assoc = db.Column(db.Integer)
    access_status = db.Column(db.Integer)
    abstract = orm.deferred(db.Column(db.Text))
    #content = orm.deferred(db.Column(db.Text))

    scopus_authors = db.relationship(
        'ScopusAuthor', secondary='scopusauthor_publication_assoc')

    def __init__(self, doi, title, scopus_id=None, pii=None, date=None,
                 pubmed_id=None, volume=None, pub_name=None, openaccess=None,
                 issue_id=None, issn=None, nif_funded=None, access_status=None,
                 nif_likelihood=None, abstract=None, content=None):  #, author_ids=()):    
        self.date = date
        self.doi = doi
        self.scopus_id = scopus_id
        self.pii = pii
        self.title = title
        self.pubmed_id = pubmed_id
        self.volume = volume
        self.pub_name = pub_name
        self.openaccess = openaccess
        self.issue_id = issue_id
        self.issn = issn
        self.nif_funded = nif_funded
        self.nif_likelihood = nif_likelihood
        self.abstract = abstract
        self.content = content
        self.access_status = access_status
        # self.author_ids = author_ids

    @property
    def content(self):
        if self.has_content:
            return None
        with open(self.content_path) as f:
            content = f.read()
        return content

    @content.setter
    def content(self, content):
        if content is not None:
            with open(self.content_path, 'w') as f:
                f.write(str(content))

    @property
    def content_path(self):
        path = os.path.join(self.CONTENT_DIR, str(self.scopus_id))
        path += ('.txt' if self.pii else '.html')
        return path

    @property
    def has_content(self):
        return os.path.exists(self.content_path)


class Affiliation(db.Model):

    __tablename__ = 'affiliations'

    id = db.Column(db.Integer, primary_key=True)
    scopus_id = db.Column(db.Integer, unique=True)
    name = db.Column(db.String(500))
    city = db.Column(db.String(100))
    country = db.Column(db.String(100))

    scopus_authors = db.relationship('ScopusAuthor', backref='affiliation')

    def __init__(self, scopus_id, name, city, country):
        self.scopus_id = scopus_id
        self.name = name
        self.city = city
        self.country = country


class ScopusAuthor(db.Model):

    __tablename__ = 'scopusauthors'

    id = db.Column(db.Integer, primary_key=True)
    scopus_id = db.Column(db.Integer, unique=True)
    researcher_id = db.Column(db.Integer,
                              db.ForeignKey(
                                  'researchers.id',
                                  name='fk_scopusauthors_researchers'))
    affiliation_id = db.Column(db.Integer,
                               db.ForeignKey(
                                   'affiliations.id',
                                   name='fk_scopusauthors_affiliations'))
    givenname = db.Column(db.String(200))
    surname = db.Column(db.String(200))
    areas = db.Column(db.String(250))

    publications = db.relationship(
        'Publication', secondary='scopusauthor_publication_assoc')

    def __init__(self, scopus_id, researcher=None, affiliation=None,
                 areas=None, givenname=None, surname=None):
        self.scopus_id = scopus_id
        self.researcher = researcher
        # self.publication = publication
        self.affiliation = affiliation
        self.areas = areas
        self.givenname = givenname
        self.surname = surname

    @property
    def name(self):
        return '{} {}'.format(self.givenname, self.surname)


scopusauthor_publication_assoc = db.Table(
    'scopusauthor_publication_assoc', db.Model.metadata,
    db.Column('id', db.Integer, primary_key=True),
    db.Column(
        'scopusauthor_id', db.String(20), db.ForeignKey(
            'scopusauthors.id',
            name='fk_scopusauthorpublicationassoc_scopusauthor')),
    db.Column(
        'publication_id', db.Integer, db.ForeignKey(
            'publications.id',
            name='fk_scopusauthorpublicationassoc_publication')))
