"""
Database models related to the instrumentation and imaging performed at the
imaging facility
"""
from app import db


class ImgType(db.Model):
    """
    The type of imaging performed in the session (e.g. 3T Human, 3T animal)
    """

    __tablename__ = 'imgtype'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)
    needs_mr_report = db.Column(db.Boolean)
    needs_pet_report = db.Column(db.Boolean)

    def __init__(self, name, needs_mr_report=True, needs_pet_report=True):
        self.name = name
        self.needs_mr_report = needs_mr_report
        self.needs_pet_report = needs_pet_report

    @property
    def reportable(self):
        "Whether the image type needs tob e reported on"
        return self.needs_mr_report or self.needs_pet_report


    def __str__(self):
        return self.name


class ImgRegion(db.Model):
    """
    The region scanned in the imaging session (e.g. Brain, Whole Body)
    """

    __tablename__ = 'imgregion'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)
    reportable = db.Column(db.Boolean)

    def __init__(self, name, reportable=True):
        self.name = name
        self.reportable = reportable


    def __str__(self):
        return self.name


class Radiopharmaceutical(db.Model):
    """
    Radiopharmaceuticals that are used at the facility
    """

    __tablename__ = 'radiopharmaceutical'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)
    halflife = db.Column(db.Float)

    projects = db.relationship(
        'Project', secondary='project_radiopharmaceutical_assoc')

    def __init__(self, name, halflife, id=None):
        if id is not None:
            self.id = id
        self.name = name
        self.halflife = halflife


    def __str__(self):
        return self.name
