#!/usr/bin/env python3
from tqdm import tqdm
from app import app, db
from app.models import Scan

# app.logger.setLevel(logging.DEBUG)
# handler = logging.StreamHandler()
# formatter = logging.Formatter("%(levelname)s - %(message)s")
# handler.setFormatter(formatter)
# app.logger.addHandler(handler)


with app.app_context():
    for scan in tqdm(Scan.query.order_by(Scan.id).all()):
        scan.label = scan.type.name
    db.session.commit()
