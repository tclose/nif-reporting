"""
Database models related to research and project setup
"""
from app import db
from app.constants import RUNNING_TITLE_LENGTH
from app.exceptions import InvalidIdError
from app.constants import QUESTIONABLE
from .imaging import ScanAttrsMixin, ScanResourceAttrsMixin


class Project(db.Model):
    """
    Project information
    """

    __tablename__ = 'project'

    id = db.Column(db.String(20), primary_key=True)
    running_title = db.Column(db.String(RUNNING_TITLE_LENGTH))
    default_priority = db.Column(db.Integer)
    risk_assessment=db.Column(db.Integer)

    radiopharmaceuticals = db.relationship(
        'Radiopharmaceutical', secondary='project_radiopharmaceutical_assoc')
    

    def __init__(self, id, running_title, default_priority=None,risk_assessment=None,
                 radiopharmaceutical=None):  # pylint: disable=redefined-builtin
        if id is None:
            raise InvalidIdError("A non-None ID must be provided to Project")
        self.id = id
        self.running_title = running_title
        self.default_priority = default_priority
        self.risk_assessment=risk_assessment
        self.radiopharmaceutical = radiopharmaceutical


    def __str__(self):
        return self.id


class Researcher(db.Model):
    """
    Researchers who use the facility
    """

    __tablename__ = 'researcher'

    id = db.Column(db.String(20), primary_key=True)
    first_name = db.Column(db.String(50))  # pylint: disable=no-member
    last_name = db.Column(db.String(50))  # pylint: disable=no-member

    def __init__(self, first_name, last_name, id=None):
        if id is not None:
            self.id = id
        self.first_name = first_name
        self.last_name = last_name


    def __str__(self):
        return self.first_name + ' ' + self.last_name


class ScanTemplate(db.Model, ScanAttrsMixin):
    """
    Specifies attributes of scans that are expected to be present in all
    sessions for a given project.
    """

    __tablename__ = 'scantemplate'

    # Fields
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(
        db.String(20), db.ForeignKey('project.id',
                                     name='fk_scantemplate_project'))
    clinical_name = db.Column(db.String(200))
    order = db.Column(db.Integer)
    # The duration of the expected resource.
    duration = db.Column(db.Float)
    tolerance = db.Column(db.Float)  # The tolerance in matching duration

    # Relationships
    project = db.relationship('Project', backref='scan_templates')

    def __init__(self, project, clinical_name=None, order=1,
                 duration=None, **kwargs):
        self.project = project
        self.clinical_name = clinical_name
        self.order = order
        self.duration = duration
        ScanAttrsMixin.__init__(self, **kwargs)

    def __repr__(self):
        return "<ScanTemplate {}:{}>".format(self.project_id, self.label)

    def matches(self, scan, min_quality=QUESTIONABLE):
        matches = (self.label == scan.label
                   and self.image_type == scan.image_type
                   and self.modality == scan.modality
                   and scan.quality > min_quality)
        return matches

    def matching_attrs(self, resource):
        def out_of_tol(a, b):
            if b is None:
                return False
            return (abs(a - b) / b) <= self.tolerance
        mismatches = []
        if self.duration is not None:
            if out_of_tol(resource.duration, self.duration):
                mismatches.append('duration')
        else:
            # Check that duration is sister resource check that they are
            # consistent
            if any(out_of_tol(resource.duration, s) for s in resource.sisters):
                mismatches.append('inconsistent_duration')
        return mismatches

    def __str__(self):
        return self.label


class ScanResourceTemplate(db.Model, ScanResourceAttrsMixin):
    """
    Specifies attributes of scan resources that are expected to be present in
    all sessions for a given project.
    """

    __tablename__ = 'scanresourcetemplate'

    # Fields
    id = db.Column(db.Integer, primary_key=True)
    scan_template_id = db.Column(
        db.Integer, db.ForeignKey(
            'scantemplate.id', name='fk_scanresourcetemplate_scantemplate'))
    tolerance = db.Column(db.Float)  # The tolerance in matching size/duration

    # Relationships
    scan_template = db.relationship('ScanTemplate', backref='resources')

    def __init__(self, scan_template, tolerance=None, **kwargs):
        self.scan_template = scan_template
        self.tolerance = tolerance
        ScanResourceAttrsMixin.__init__(self, **kwargs)

    def matching_attrs(self, resource):
        mismatches = []
        if self.num_files is not None and self.num_files != resource.num_files:
            mismatches.append('num_files')

        def out_of_tol(a, b):
            if b is None:
                return False
            return (abs(a - b) / b) <= self.tolerance
        if out_of_tol(resource.size, self.size):
            mismatches.append('size')
        return mismatches


    def __str__(self):
        return self.type


project_radiopharmaceutical_assoc = db.Table(
    'project_radiopharmaceutical_assoc', db.Model.metadata,
    db.Column('id', db.Integer, primary_key=True),
    db.Column(
        'project_id', db.String(20), db.ForeignKey(
            'project.id', name='fk_projectradiopharmaceuticalassoc_project')),
    db.Column(
        'radiopharmaceutical_id', db.Integer, db.ForeignKey(
            'radiopharmaceutical.id',
            name='fk_projectradiopharmaceuticalassoc_radiopharmaceutical')))
