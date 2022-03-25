from __future__ import annotations

import asyncio
import typing
from datetime import datetime
from logging.config import fileConfig
from typing import Type

import sqlalchemy as sa
from alembic.autogenerate import comparators, renderers
from alembic.autogenerate.api import AutogenContext
from alembic.operations import MigrateOperation, Operations, ops
import sqlalchemy.orm as orm

from alembic import context
from sqlalchemy.sql import ClauseElement, Select
from sqlalchemy.sql.compiler import SQLCompiler
from sqlalchemy_utils.view import CreateView, DropView

from btrfs_recon.db import engine, sync_engine
from btrfs_recon.persistence import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata
orm.configure_mappers()

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


@Operations.register_operation('drop_view')
class DropViewOp(MigrateOperation):
    """Drop a VIEW or MATERIALIZED VIEW"""

    def __init__(
        self,
        view_name: str,
        *,
        materialized: bool = False,
        _reverse_query: Select | str | None = None,
    ):
        self.view_name = view_name
        self.materialized = materialized
        self._reverse_query = _reverse_query

    @classmethod
    def drop_view(cls, operations: Operations, view_name: str, **kw):
        """Issue a DROP [MATERIALIZED] VIEW instruction"""
        op = DropViewOp(view_name, **kw)
        return operations.invoke(op)

    @classmethod
    def from_view(cls, view_cls: type) -> DropViewOp:
        from btrfs_recon.persistence.models._views import View, MaterializedView

        if not issubclass(view_cls, View):
            raise ValueError(f'{view_cls} is not a View class')

        materialized = issubclass(view_cls, MaterializedView)
        return DropViewOp(
            view_name=view_cls.__tablename__,
            materialized=materialized,
            _reverse_query=view_cls.__query__,
        )

    def reverse(self) -> MigrateOperation:
        if self._reverse_query is not None:
            return CreateViewOp(
                view_name=self.view_name,
                materialized=self.materialized,
                query=self._reverse_query,
            )
        else:
            raise ValueError(
                'view cannot be produced; original view query is not present'
            )


@Operations.implementation_for(DropViewOp)
def drop_view(operations: Operations, operation: DropViewOp):
    operations.execute(DropView(operation.view_name, materialized=operation.materialized))


@Operations.register_operation('create_view')
class CreateViewOp(MigrateOperation):
    """Create a VIEW or MATERIALIZED VIEW"""

    def __init__(
        self,
        view_name: str,
        query: Select | str | None,
        *,
        materialized: bool = False,
    ):
        self.view_name = view_name
        self.query = query
        self.materialized = materialized

    @classmethod
    def create_view(cls, operations: Operations, view_name: str, query: str, **kw):
        """Issue a CREATE [MATERIALIZED] VIEW instruction"""
        op = CreateViewOp(view_name, query, **kw)
        return operations.invoke(op)

    @classmethod
    def from_view(cls, view_cls: type) -> CreateViewOp:
        from btrfs_recon.persistence.models._views import View, MaterializedView

        if not issubclass(view_cls, View):
            raise ValueError(f'{view_cls} is not a View class')

        materialized = issubclass(view_cls, MaterializedView)
        return CreateViewOp(
            view_name=view_cls.__tablename__,
            query=view_cls.__query__,
            materialized=materialized,
        )

    def reverse(self) -> MigrateOperation:
        return DropViewOp(
            view_name=self.view_name,
            materialized=self.materialized,
            _reverse_query=self.query,
        )


@Operations.implementation_for(CreateViewOp)
def create_view(operations: Operations, op: CreateViewOp):
    operations.execute(
        CreateView(op.view_name, sa.text(op.query), materialized=op.materialized)
    )


class LiteralCompilerMixin:
    def visit_bindparam(
        self,
        bindparam,
        within_columns_clause=False,
        literal_binds=False,
        **kwargs
    ):
        return super().render_literal_bindparam(
            bindparam,
            within_columns_clause=within_columns_clause,
            literal_binds=literal_binds,
            **kwargs,
        )

    def render_literal_value(self, value, type_):
        if value is None:
            return 'NULL'
        elif isinstance(value, datetime):
            return repr(str(value))
        else:
            return super().render_literal_value(value, type_)

    def process(self, obj, **kwargs):
        kwargs.setdefault('literal_binds', True)
        return super().process(obj, **kwargs)


@comparators.dispatch_for('schema')
def compare_views(autogen_context: AutogenContext, upgrade_ops, schemas):
    discovered_views_map: dict[tuple[str, bool], str] = {}

    schema_names = [
        autogen_context.dialect.default_schema_name if n is None else n
        for n in schemas
    ]

    discovered_views_map.update({
        (view_name, False): query
        for view_name, query in autogen_context.connection.execute(
            sa.select(
                sa.column('viewname', type_=sa.String),
                sa.column('definition', type_=sa.String),
            )
            .select_from(sa.text('pg_views'))
            .filter(
                sa.column('schemaname', type_=sa.String).in_(schema_names)
            )
        )
    })
    discovered_views_map.update({
        (view_name, True): query
        for view_name, query in autogen_context.connection.execute(
            sa.select(
                sa.column('matviewname', type_=sa.String),
                sa.column('definition', type_=sa.String),
            )
            .select_from(sa.text('pg_matviews'))
            .filter(
                sa.column('schemaname', type_=sa.String).in_(schema_names)
            )
        )
    })
    discovered_views: set[tuple[str, str, bool]] = {
        (view_name, query, materialized)
        for (view_name, materialized), query in discovered_views_map.items()
    }

    base_compiler_cls = autogen_context.dialect.statement_compiler
    sql_compiler_cls: Type[SQLCompiler] = typing.cast(
        Type[SQLCompiler],
        type(
            f'Literal_{base_compiler_cls.__name__}', (LiteralCompilerMixin, base_compiler_cls), {}
        ),
    )

    def compile_statement(statement: ClauseElement) -> str:
        sql_compiler = sql_compiler_cls(autogen_context.dialect, statement)
        sql = sql_compiler.process(statement)
        return sql

    registered_views = autogen_context.metadata.info.setdefault('views', set())
    # Ensure queries are compiled
    registered_views = {
        (
            view_name,
            str(query if isinstance(query, str) else compile_statement(query)),
            materialized,
        )
        for view_name, query, materialized in registered_views
    }
    registered_views_map = {
        (view_name, materialized): query
        for view_name, query, materialized in registered_views
    }

    # For new views, produce CreateViewOp directives
    for view_name, materialized in set(registered_views_map) - set(discovered_views_map):
        query = registered_views_map[view_name, materialized]
        upgrade_ops.ops.append(
            CreateViewOp(view_name, query, materialized=materialized)
        )

    # For changed views, produce DropViewOp followed by CreateViewOp directives
    existing_views = set(registered_views_map) & set(discovered_views_map)
    changed_views = existing_views & {
        (view_name, materialized)
        for view_name, query, materialized in set(registered_views) - set(discovered_views)
    }
    for view_name, materialized in changed_views:
        new_query = registered_views_map[view_name, materialized]
        old_query = discovered_views_map[view_name, materialized]
        upgrade_ops.ops.extend((
            DropViewOp(view_name, materialized=materialized, _reverse_query=old_query),
            CreateViewOp(view_name, new_query, materialized=materialized),
        ))

    # For deleted views, produce DropViewOp directives
    for view_name, materialized in set(discovered_views_map) - set(registered_views_map):
        old_query = discovered_views_map[view_name, materialized]
        upgrade_ops.ops.append(
            DropViewOp(view_name, materialized=materialized, _reverse_query=old_query)
        )


@renderers.dispatch_for(DropViewOp)
def render_drop_view(autogen_context: AutogenContext, op: DropViewOp):
    return f'op.drop_view({op.view_name!r}, materialized={op.materialized!r})'


@renderers.dispatch_for(CreateViewOp)
def render_create_view(autogen_context: AutogenContext, op: CreateViewOp):
    return f'op.create_view({op.view_name!r}, {op.query!r}, materialized={op.materialized!r})'


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    with sync_engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
        )

        with context.begin_transaction():
            context.run_migrations()


def process_revision_directives(context, revision, directives):
    script = directives[0]
    view_names = {
        view_name
        for view_name, query, materialized in Base.metadata.info.setdefault('views', set())
    }

    for directive in (script.upgrade_ops, script.downgrade_ops):
        directive.ops = [
            op
            for op in directive.ops
            if not (
                isinstance(op, (ops.CreateTableOp, ops.DropTableOp))
                and op.table_name in view_names
            )
        ]


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        user_module_prefix='btrfs_recon.persistence.fields.',
        process_revision_directives=process_revision_directives,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
