from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from domain_config import list_domain_templates
from models import DomainTemplate


router = APIRouter()


@router.get("/templates")
def get_domain_templates(db: Session = Depends(get_db)):
    rows = db.query(DomainTemplate).order_by(DomainTemplate.domain.asc()).all()
    if rows:
        return {
            "templates": [row.config for row in rows],
        }
    return {
        "templates": [template.model_dump(mode="json") for template in list_domain_templates()],
    }

