import re
from sqlalchemy import orm
from app import db, app
from app.constants import (
    REPORT_PRIORITY, PRIORITY_DEFAULT, NOT_SCANNED, EXCLUDED,
    PRESENT, UNKNOWN, MRI, PET, DATA_STATUS, SCAN_QUALITY)
from app.utils.sql import within_interval
from app.exceptions import InvalidIdError
from .reporting import Report
from .facility import ImgType, ImgRegion


DAYS_IN_YEAR = 365.2425


class ImgSession(db.Model):
    """
    Details of the imaging session
    """

    __tablename__ = 'imgsession'

    # Fields
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(
        db.String(20), db.ForeignKey('project.id',
                                     name='fk_imgsession_project'))
    subject_id = db.Column(
        db.String(20), db.ForeignKey('subject.id',
                                     name='fk_imgsession_subject'))
    xnat_subject_id = db.Column(db.String(100))
    xnat_visit_id = db.Column(db.String(100))
    daris_code = db.Column(db.String(50))
    scan_date = db.Column(db.Date())
    priority = db.Column(db.Integer)
    data_status = db.Column(db.Integer)
    height = db.Column(db.Float)
    weight = db.Column(db.Float)
    notes = orm.deferred(db.Column(db.Text))
    radiographer_notes = orm.deferred(db.Column(db.Text))
    # We save this in the imgsession table so it can be accessed by the
    # radiologist when they are reporting from an external mirror
    age_at_scan = db.Column(db.Integer)
    # Used to signify whether the record has been edited in the admin portal
    # (as opposed to changed between FileMaker reports) to avoid overwriting
    # when syncing with Filemaker
    edited = db.Column(db.Boolean)

    # Do these need to go in project not study?
    image_type_id = db.Column(
        db.Integer, db.ForeignKey('imgtype.id',
                                  name='fk_imgsession_imagetype'))
    image_region_id = db.Column(
        db.Integer, db.ForeignKey('imgregion.id',
                                  name='fk_imgsession_imageregion'))
    # The IDs that XNAT uses internally to differentiate sessions and subjects.
    # It is faster to look up sessions with it rather than the project/session
    # ID pair.
    internal_xnat_id = db.Column(db.String(50))
    internal_xnat_subject_id = db.Column(db.String(50))
    # Radiographer who flagged the session for urgent reporting
    radiographer_id = db.Column(
        db.Integer, db.ForeignKey('user.id',
                                  name='fk_imgsession_user_radiographer'))

    # The time that a report was opened for this session. Used to exclude other
    # users from reporting on the session at the same time (and duplicate
    # reports). After ACTIVE_REPORTER_EXCLUSION_PERIOD lapses the session is
    # added back into the queue
    locked_by_id = db.Column(
        db.Integer, db.ForeignKey('user.id',
                                  name='fk_imgsession_subject_lockedby'),
        nullable=True)
    lock_start = db.Column(db.DateTime)

    # Relationships
    project = db.relationship('Project', backref='sessions')
    subject = db.relationship('Subject', backref='sessions')
    image_type = db.relationship('ImgType', backref='sessions')
    image_region = db.relationship('ImgRegion', backref='sessions')
    radiographer = db.relationship('User', backref='flagged_sessions',
                                   foreign_keys=[radiographer_id])
    locked_by = db.relationship('User', backref='locked_sessions',
                                foreign_keys=[locked_by_id])
    screeningform = db.relationship('ScreeningForm',
                                    backref='imgsession', uselist=False)
    report = db.relationship('Report', backref='session', uselist=False)

    def __init__(self, project, subject, xnat_subject_id, xnat_visit_id,  # noqa pylint: disable=redefined-builtin
                 scan_date, data_status=UNKNOWN, height=None, weight=None,
                 notes=None, priority=None, daris_code=None, image_type=None,
                 image_region=None, radiographer_notes=None,
                 internal_xnat_id=None, internal_xnat_subject_id=None,
                 image_data=None, id=None):
        if priority is None:
            if project.default_priority is not None:
                priority = project.default_priority
            else:
                priority = PRIORITY_DEFAULT
        # Convert datetime to date if required
        try:
            scan_date = scan_date.date()
        except AttributeError:
            pass
        if id is not None:
            self.id = id
        self.project = project
        self.subject = subject
        self.xnat_subject_id = xnat_subject_id
        self.xnat_visit_id = xnat_visit_id
        self.scan_date = scan_date
        self.data_status = data_status
        self.height = height
        self.weight = weight
        self.notes = notes
        self.priority = priority
        self.daris_code = daris_code
        self.image_type = image_type
        self.image_region = image_region
        self.radiographer_notes = radiographer_notes
        self.internal_xnat_id = internal_xnat_id
        self.internal_xnat_subject_id = internal_xnat_subject_id
        self.image_data = image_data
        self.set_age_at_scan()

    def set_age_at_scan(self):
        if self.subject.dob is not None:
            self.age_at_scan = int(
                (self.scan_date - self.subject.dob).days / DAYS_IN_YEAR)

    def __repr__(self):
        return '<Session {}>'.format(self.xnat_id)

    @property
    def priority_str(self):
        return REPORT_PRIORITY[self.priority][0]

    @property
    def priority_desc(self):
        return REPORT_PRIORITY[self.priority][1]

    @property
    def data_status_str(self):
        return DATA_STATUS[self.data_status][0]

    @property
    def data_status_desc(self):
        return DATA_STATUS[self.data_status][1]

    @property
    def not_present(self):
        return self.data_status != PRESENT

    @property
    def scan_date_str(self):
        return self.scan_date.strftime('%d/%m/%Y')

    @property
    def is_mr_pet(self):
        return any(s.type.clinical_pet for s in self.scans)

    @property
    def xnat_id(self):
        # NB: The None checks are just for legacy sessions that don't have
        # IDs entered.
        return '{}_{}_{}'.format(
            self.project.id,
            (self.xnat_subject_id
             if self.xnat_subject_id is not None else ''),
            (self.xnat_visit_id
             if self.xnat_visit_id is not None else ''))

    @property
    def full_xnat_subject_id(self):
        return '{}_{}'.format(self.project.id, self.xnat_subject_id)

    @classmethod
    def get_from_xnat_id(cls, xnat_id):
        match = re.match(
            r'([a-zA-Z0-9]+)_([a-zA-Z0-9]+)_([a-zA-Z]+[0-9]+)',
            xnat_id)
        if match is None:
            raise InvalidIdError(
                "Provided XNAT ID '{}' doesn't match convention (i.e. "
                "<PROJECTID>_<SUBJECTID>_<MODALITY><VISITID>".format(xnat_id))
        proj_id, subj_id, visit_id = match.groups()
        try:
            return cls.query.filter_by(project_id=proj_id,
                                       xnat_subject_id=subj_id,
                                       xnat_visit_id=visit_id).one()
        except orm.exc.NoResultFound:
            raise InvalidIdError(
                "Did not find session matching XNAT ID '{}'".format(xnat_id))

    @classmethod
    def require_report(cls, modality=MRI):
        """
        Returns a query that selects all imaging sessions that still need to be
        reported
        """
        if modality not in (MRI, PET):
            raise Exception("Unrecognised modality {}, can be {} (MRI) or {} "
                            "(PET)".format(modality, MRI, PET))
        # Create an alias of the ImgSession model so we can search within
        # its table for more recent sessions and earlier sessions that have
        # been reported
        S = orm.aliased(ImgSession)
        IR = orm.aliased(ImgRegion)

        if modality == MRI:
            img_type_reportable = ImgType.needs_mr_report
        else:
            img_type_reportable = ImgType.needs_pet_report

        # Create query for sessions that still need to be reported
        require_report = (
            db.session.query(ImgSession)
            .join(ImgType)
            .join(ImgRegion)
            .filter(
                img_type_reportable,
                ImgRegion.reportable,
                ~ImgSession.data_status.in_([NOT_SCANNED, EXCLUDED]),
                # Filter out sessions of the same imaging region in subjects
                # that have a more recent session
                ~(db.session.query(S.id)
                  .join(IR)
                  .filter(
                      S.subject_id == ImgSession.subject_id,
                      IR.id == ImgRegion.id,
                      S.scan_date > ImgSession.scan_date,
                      ~S.data_status.in_([NOT_SCANNED, EXCLUDED])).exists()),
                # Filter out sessions of the same imaging region subjects that
                # have been reported on less than the REPORT_INTERVAL (e.g. 365
                # days) beforehand
                ~(db.session.query(S.id)
                  .join(Report)  # Only select sessions with a report
                  .join(IR)
                  .filter(
                      S.subject_id == ImgSession.subject_id,
                      IR.id == ImgRegion.id,
                      Report.modality == modality,
                      within_interval(
                          S.scan_date,
                          ImgSession.scan_date,
                          app.config['REPORT_INTERVAL'])).exists())))

        return require_report

    @property
    def xnat_uri(self):
        uri = app.config['XNAT_URL'] + '/data'
        if self.internal_xnat_id is not None:
            uri += '/experiments/' + self.internal_xnat_id
        else:
            uri += '/projects/{}/experiments/{}'.format(self.project_id,
                                                        self.xnat_id)
        return uri

    @property
    def xnat_subject_uri(self):
        return (app.config['XNAT_URL']
                + '/data/projects/{}/subjects/{}'.format(self.project_id,
                                                         self.xnat_subject_id))

    @property
    def xnat_project_uri(self):
        return (app.config['XNAT_URL']
                + '/data/projects/{}/'.format(self.project_id))

    def __str__(self):
        return str(self.id)


class ScanAttrsMixin():
    """
    Mixin class used to list scan attributes that are potentially recorded and
    checked for in the 'Scan' and 'ScanTemplate' classes respectively
    """

    label = db.Column(db.String(300))
    modality = db.Column(db.String(50))
    image_type = db.Column(db.String(200))

    def __init__(self, label, modality=None, image_type=None):
        self.label = label
        self.image_type = image_type
        self.modality = modality


class ScanResourceAttrsMixin():
    """
    Mixin class used to list scan resource attributes that are potentially
    recorded and checked for in the 'ScanResource' and
    'ScanResourceTemplate' classes respectively
    """

    type = db.Column(db.String(50))
    num_files = db.Column(db.Integer)
    size = db.Column(db.Integer)

    def __init__(self, type, size=None, num_files=None):
        self.type = type
        self.num_files = num_files
        self.size = size


class Scan(db.Model, ScanAttrsMixin):
    """
    A scan within an imaging session
    """

    __tablename__ = 'scan'

    # Fields
    id = db.Column(db.Integer, primary_key=True)
    xnat_id = db.Column(db.String(100))
    session_id = db.Column(
        db.Integer, db.ForeignKey('imgsession.id',
                                  name='fk_scan_imgsession'))
    type_id = db.Column(
        db.Integer, db.ForeignKey('scantype.id',
                                  name='fk_scan_scantype'))
    status = db.Column(db.Integer)
    quality = db.Column(db.Integer)
    template_match_id = db.Column(
        db.Integer, db.ForeignKey('scantemplate.id',
                                  name='fk_scan_scantemplate'))

    # Relationships
    type = db.relationship('ScanType', backref='scans')
    session = db.relationship('ImgSession', backref='scans')
    reports = db.relationship('Report', secondary='report_scan_assoc')
    template_match = db.relationship('ScanTemplate', backref='matches')

    def __init__(self, xnat_id, session, status=None, quality=None,
                 **kwargs):
        self.xnat_id = xnat_id
        self.session = session
        self.status = status
        if isinstance(quality, int):
            self.quality = quality
        else:
            self.quality_str = quality
        ScanAttrsMixin.__init__(self, **kwargs)

    def __repr__(self):
        return "<Scan {}>".format(str(self))

    def __getitem__(self, resource_type):
        try:
            return next(r for r in self.resources if r.type == resource_type)
        except StopIteration:
            return KeyError(resource_type)

    def __str__(self):
        return "[{}] {}".format(self.xnat_id, self.label_str)

    @property
    def label_str(self):
        if self.type:
            label = self.type.name
        else:
            label = self.label
        return label

    @property
    def quality_str(self):
        return SCAN_QUALITY[self.quality][0]

    @quality_str.setter
    def quality_str(self, quality_str):
        if quality_str is None:
            self.quality = None
        else:
            self.quality = {v[0]: k
                            for k, v in SCAN_QUALITY.items()}[quality_str]


class ScanResource(db.Model, ScanResourceAttrsMixin):
    """
    A resource within a scan (e.g. DICOM, LISTMODE, KSPACE)
    """

    __tablename__ = 'scanresource'

    id = db.Column(db.Integer, primary_key=True)
    scan_id = db.Column(
        db.Integer, db.ForeignKey('scan.id', name='fk_scanresource_scan'))
    # Duration of the resource. Saved separately for each resource just in
    # case one of the resources has been truncated in the storage process.
    duration = db.Column(db.Float)

    scan = db.relationship('Scan', backref='resources')

    def __init__(self, scan, duration=None, **kwargs):
        ScanResourceAttrsMixin.__init__(self, **kwargs)
        self.duration = duration
        self.scan = scan

    @property
    def sisters(self):
        return (r for r in self.scan.resources if r is not self)


    def __str__(self):
        return self.type


class ScanType(db.Model):
    """
    The type of (clinically relevant) scans in the session
    """

    __tablename__ = 'scantype'

    is_clinical_mri_re = re.compile(
        r'(?i)(?!.*kspace.*).*(?<![a-zA-Z])(t1).*|'
        r'(?!.*kspace.*).*(?<![a-zA-Z])(t2).*|'
        r'(?!.*kspace.*).*(mprage).*|'
        r'(?!.*kspace.*).*(qsm).*|'
        r'(?!.*kspace.*).*(flair).*|'
        r'(?!.*kspace.*).*(fl3d).*')

    is_clinical_pet_re = re.compile(r'.*AC Images.*')

    # Fields
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True)
    clinical_mri = db.Column(db.Boolean)
    clinical_pet = db.Column(db.Boolean)
    confirmed = db.Column(db.Boolean)

    def __init__(self, name):
        self.name = name
        self.clinical_mri = bool(self.is_clinical_mri_re.match(name))
        self.clinical_pet = bool(self.is_clinical_pet_re.match(name))
        self.confirmed = False

    def __repr__(self):
        return "<ScanType {}>".format(self.name)
