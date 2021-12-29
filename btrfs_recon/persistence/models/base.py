__all__ = ['Base', 'BaseModel']

from datetime import datetime

import inflection
import sqlalchemy as sa
from sqlalchemy.orm import declarative_base, declared_attr

Base = declarative_base()


class BaseModel(Base):
    __abstract__ = True

    @declared_attr
    def __tablename__(cls) -> str:
        return inflection.underscore(cls.__name__)

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)

    created_at = sa.Column(sa.DateTime, default=datetime.utcnow, server_default=sa.func.now(), nullable=False)
    updated_at = sa.Column(sa.DateTime, default=datetime.utcnow, server_default=sa.func.now(), server_onupdate=sa.func.now(), nullable=False)
