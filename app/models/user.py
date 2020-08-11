import os.path as op
from collections.abc import Iterable
from sqlalchemy import sql
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import deferred
from app import db
from app.constants import (USER_STATUS, ACTIVE, NEW_USER)
from app.exceptions import UploadTooLargeException


Base = declarative_base()


class User(db.Model):
    """
    Model representing a user of the application, either a radiologist or admin
    user (or both) as specified by the user_role_assoc table.

    Parameters
    ----------
    id : int
        ID of the User
    title : str
        User's title (e.g. Ms)
    first_name : str
        User's first name
    last_name : str
        User's last name
    middle_name : str
        User's middle_name
    email : str
        User's email
    password : str
        User's password
    status : int
        Status of the user. Can be NEW_USER, ACTIVE or INACTIVE
    signature : str
        The path to the uploaded image containing the User's electronic
        signature
    """

    __tablename__ = 'user'

    # Fields
    id = db.Column(db.Integer, primary_key=True)
    affiliation_id = db.Column(db.Integer,
                               db.ForeignKey('affiliation.id',
                                             name='fk_user_affiliation'))
    title = db.Column(db.String(10))
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    middle_name = db.Column(db.String(50))
    suffixes = db.Column(db.String(30))
    email = db.Column(db.String(120), unique=True)
    mobile = db.Column(db.String(20))
    password = db.Column(db.String(120))
    status = db.Column(db.Integer())
    token = db.Column(db.String(50))  # Used to reset passwords
    token_expiry = db.Column(db.DateTime())

    # Relationships
    signature = db.relationship('UserSignature', backref='user', uselist=False)
    affiliation = db.relationship('Affiliation', backref='users')

    def __init__(self, first_name, last_name, email, password,
                 middle_name=None, suffixes=None, title=None,
                 mobile=None, signature=None, status=NEW_USER):
        self.title = title
        self.first_name = first_name
        self.last_name = last_name
        self.middle_name = middle_name
        self.suffixes = suffixes
        self.email = email
        self.password = password
        self.mobile = mobile
        self.status = status
        self.signature = signature

    @property
    def status_str(self):
        return USER_STATUS[self.status][0]

    @property
    def status_desc(self):
        return USER_STATUS[self.status][1]

    @property
    def active(self):
        return self.status == ACTIVE

    @property
    def name(self):
        return '{} {}'.format(self.first_name, self.last_name)

    @property
    def name_and_title(self):

        def if_not_none(f, frmt_str='{} '):
            return frmt_str.format(f) if f is not None else ''

        return '{}{} {}{}{}'.format(
            if_not_none(self.title),
            self.first_name,
            if_not_none(self.middle_name),
            self.last_name,
            if_not_none(self.suffixes, ', {}'))

    def __repr__(self):
        return "<User '{}'>".format(self.name)

    def is_authorised(self, acceptable_roles):
        """
        Checks whether the user has the required role

        Parameters
        ----------
        acceptable_roles : int | list[int]
            The role IDs that are authorised
        """

        if not isinstance(acceptable_roles, Iterable):
            acceptable_roles = [acceptable_roles]
        for role in self.roles:
            if role in acceptable_roles:
                return True
        return False

    @property
    def roles(self):
        if self.id is None:
            raise Exception("User '{}' must be commited to database before "
                            "roles can be set".format(self.name))
        return (r[0] for r in db.session.execute(
            sql.select([user_role_assoc.c.role_id])
            .where(user_role_assoc.c.user_id == self.id)).fetchall())

    @roles.setter
    def roles(self, roles):
        roles = set(roles)
        current_roles = set(self.roles)
        roles_to_add = roles - current_roles
        if roles_to_add:
            db.session.execute(
                sql.insert(user_role_assoc)
                .values(
                    [{'user_id': self.id, 'role_id': i}
                     for i in roles_to_add]))
        roles_to_delete = current_roles - roles
        if roles_to_delete:
            db.session.execute(
                sql.delete(user_role_assoc)
                .where(
                    user_role_assoc.c.user_id == self.id)
                .where(
                    user_role_assoc.c.role_id.in_(roles_to_delete)))
        db.session.commit()

    def __str__(self):
        return self.first_name + ' ' + self.last_name


class Affiliation(db.Model):
    """
    The affiliation of a user, used when generating radiological report PDFs
    and sending monthly summary of completed reports
    """
    __tablename__ = 'affiliation'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(500))
    abbrev = db.Column(db.String(50))
    admin_email = db.Column(db.String(100))  # Used to send monthly summaries
    # The following columns are used in the generation of the report PDFs
    abn = db.Column(db.String(20))
    phone = db.Column(db.String(20))
    fax = db.Column(db.String(20))
    website = db.Column(db.String(100))
    department = db.Column(db.String(500))
    ea_name = db.Column(db.String(100))
    contact_phone = db.Column(db.String(20))
    contact_email = db.Column(db.String(100))
    address = deferred(db.Column(db.Text))

    def __init__(self, name, abbrev, admin_email, abn, phone, fax, website,
                 department, contact_phone, contact_email, address,
                 ea_name=None):
        self.name = name
        self.abbrev = abbrev
        self.admin_email = admin_email
        self.address = address
        self.abn = abn
        self.phone = phone
        self.fax = fax
        self.website = website
        self.department = department
        self.ea_name = ea_name
        self.contact_phone = contact_phone
        self.contact_email = contact_email


    def __str__(self):
        return self.abbrev


class UserSignature(db.Model):
    """
    Store the signature image associated with the user in a separate table.
    We store it in the database rather than on disk so it is accessible from
    both external (write only) and internal mirrors.
    """
    __tablename__ = 'usersignature'

    MAX_IMAGE_SIZE = 2 ** 20  # 1 MB

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', name='fk_usersignature_user'),
        unique=True)
    image_data = db.Column(db.LargeBinary)
    mimetype = db.Column(db.String(50))

    def __init__(self, user_id, image_data, mimetype):
        self.user_id = user_id
        if len(image_data) > self.MAX_IMAGE_SIZE:
            one_mb = 2 ** 20
            raise UploadTooLargeException(
                ("Signature image file is too large to be uploaded ({} MB, "
                 "max {} MB)").format(round(len(image_data) / one_mb, 2),
                                      round(self.MAX_IMAGE_SIZE / one_mb, 2)))
        self.image_data = image_data
        self.mimetype = mimetype

    @classmethod
    def from_file(cls, user_id, file_path):
        # Read image data
        with open(file_path, 'rb') as f:
            image_data = f.read()
        # Get mimetype
        ext = op.splitext(file_path)[-1][1:]
        if ext.lower() == 'jpg':
            ext = 'jpeg'
        mimetype = 'image/' + ext.lower()
        return cls(user_id, image_data, mimetype)


user_role_assoc = db.Table(
    'user_role_assoc', db.Model.metadata,
    db.Column('id', db.Integer, primary_key=True),
    db.Column('user_id', db.Integer,
              db.ForeignKey('user.id', name='fk_userroleassoc_user')),
    db.Column('role_id', db.Integer))
