from typing import Type

import sqlalchemy as sa
import sqlalchemy.event
import sqlalchemy.orm as orm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_utils import create_materialized_view, create_view, refresh_materialized_view

from .base import Base


class View(Base):
    __abstract__ = True

    @orm.declared_attr
    def __query__(cls) -> sa.sql.Select:
        """Return the query used to populate the view"""
        raise NotImplementedError


class MaterializedView(View):
    __abstract__ = True

    @classmethod
    async def refresh(cls, session: AsyncSession, *, concurrently: bool = False) -> None:
        """REFRESH the materialized view"""
        # NOTE: the following comment and flush is taken directly from sqlalchemy_utils
        # Since session.execute() bypasses autoflush, we must manually flush in
        # order to include newly-created/modified objects in the refresh.
        await session.flush()

        query_components = ['REFRESH MATERIALIZED VIEW']
        if concurrently:
            query_components.append('CONCURRENTLY')

        view_name = cls.__tablename__
        quoted_name = session.bind.engine.dialect.identifier_preparer.quote(view_name)
        query_components.append(quoted_name)

        query = ' '.join(query_components) + ';'
        await session.execute(query)

    @classmethod
    def refresh_sync(cls, session: orm.Session, *, concurrently: bool = False) -> None:
        refresh_materialized_view(session, cls.__tablename__, concurrently=concurrently)


@sa.event.listens_for(View, 'mapper_configured')
def on_view_class_init(mapper: orm.Mapper, cls: Type[View]):
    if issubclass(cls, MaterializedView):
        create_materialized_view(cls.__tablename__, cls.__query__, cls.metadata)
    elif issubclass(cls, View):
        create_view(cls.__tablename__, cls.__query__, cls.metadata)
    else:
        raise TypeError(f'Received mapper_configured event for non-View class {cls}')
