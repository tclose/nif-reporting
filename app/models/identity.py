import random
from sqlalchemy.ext.hybrid import hybrid_property
from app import db
from app.constants import GENDER


class Subject(db.Model):
    """
    Basic information about the subject of the imaging session. It is
    separated from the imaging session so that we can check for multiple
    in a year (or other arbitrary period) and only provide the latest one.
    """

    __tablename__ = 'subject'

    # Fields
    id = db.Column(db.String(20), primary_key=True)  # noqa pylint: disable=no-member
    first_name = db.Column(db.String(100))  # pylint: disable=no-member
    last_name = db.Column(db.String(100))  # pylint: disable=no-member
    middle_name = db.Column(db.String(100))  # pylint: disable=no-member
    _gender = db.Column(db.Integer)  # pylint: disable=no-member
    dob = db.Column(db.Date())  # pylint: disable=no-member
    animal_id = db.Column(db.String(100))  # pylint: disable=no-member

    NUM_ID_DIGITS = 6

    def __init__(self, id, first_name, last_name, gender, dob,  # noqa pylint: disable=redefined-builtin
                 middle_name=None, animal_id=None):
        self.id = id
        self.first_name = first_name
        self.last_name = last_name
        self.gender = gender
        self.dob = dob
        self.middle_name = middle_name
        self.animal_id = animal_id

    def __repr__(self):
        return '<Subject {}>'.format(self.id)

    @property
    def dob_str(self):
        return self.dob.strftime('%d/%m/%Y')

    @property
    def dob_dicom_str(self):
        return self.dob.strftime('%Y%d%m')

    @property
    def name(self):
        return '{}{} {}'.format(
            self.first_name,
            (' ' + self.middle_name if self.middle_name else ''),
            self.last_name)

    @hybrid_property
    def gender(self):
        return self._gender

    @gender.setter
    def gender(self, gender):
        try:
            self._gender = int(gender) if gender is not None else None
        except ValueError:
            # reverse gender dictionary
            try:
                self._gender = next(k for k, v in GENDER.items()
                                    if v == gender.lower())
            except StopIteration:
                raise Exception(
                    "No gender matches provided value '{}'".format(gender))

    def gender_str(self):
        return GENDER[self._gender]

    @classmethod
    def generate_new_id(cls):
        existing = set(int(r[0][3:])  # Strip 'MSH' from IDs
                       for r in cls.query.with_entities(cls.id).all())
        possible = set(range(10 ** cls.NUM_ID_DIGITS))
        return 'MSH{}'.format(random.choice(list(possible - existing)))

    def __str__(self):
        return self.id


class ContactInfo(db.Model):
    """
    Basic information about the subject of the imaging session. It is
    separated from the imaging session so that we can check for multiple
    in a year (or other arbitrary period) and only provide the latest one.

    Parameters
    ----------
    subject_id : Subject ID
        The subject the contact details are for
    entry_date : Date
        The date the contact details were entered into the system
    street : str
        The street address, name and number
    suburb : str
        The suburb of the address
    mobile_phone : str
        A contact mobile phone number
    work_phone : str
        A contact work phone number
    country : str | None
        The country, if left None it is assumed to be Australia
    """

    __tablename__ = 'contact_info'
    __table_args__ = (
        db.UniqueConstraint('subject_id', 'entry_date',
                            name='unique_subject_entrydate'),)

    # Fields
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(
        db.String(20), db.ForeignKey('subject.id',
                                     name='fk_contactinfo_subject'))
    entry_date = db.Column(db.Date())
    street = db.Column(db.String(100))
    suburb = db.Column(db.String(100))
    postcode = db.Column(db.String(100))
    country = db.Column(db.String(100))
    mobile_phone = db.Column(db.String(100))
    work_phone = db.Column(db.String(100))

    # Relationships
    subject = db.relationship('Subject', backref='contact_infos')

    def __init__(self, subject_id, entry_date, street, suburb, postcode,
                 mobile_phone=None, work_phone=None, country=None):
        self.subject_id = subject_id
        self.entry_date = entry_date
        self.street = street
        self.suburb = suburb
        self.postcode = postcode
        self.mobile_phone = mobile_phone
        self.work_phone = work_phone
        self.country = country

    def __repr__(self):
        return '<ContactInfo {} - {}>'.format(
            self.subject.id, self.date.strftime('%d/%m/%Y'))

    def __str__(self):
        return self.street


class ScreeningForm(db.Model):
    """
    Store the session's subject screening form.
    We store it in the database rather than on disk so it is accessible from
    both external (write only) and internal mirrors.
    """

    __tablename__ = 'screeningform'
    id = db.Column(db.Integer, primary_key=True)  # session id
    pdf_data = db.Column(db.LargeBinary)
    session_id = db.Column(db.ForeignKey('imgsession.id',
                                         name='fk_screeningform_imgsession'))

    def __init__(self, id, pdf_data, session):
        self.id = id
        self.pdf_data = pdf_data
        self.session = session
