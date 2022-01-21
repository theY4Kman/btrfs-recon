#!/usr/bin/env python
from __future__ import annotations

import importlib
import sys
from collections import defaultdict
from datetime import datetime
from typing import Any, Collection, Iterable, Optional, Type, Union

import asyncclick as click
import nest_asyncio
from IPython.terminal.interactiveshell import TerminalInteractiveShell
from IPython.terminal.ipapp import TerminalIPythonApp
from sqlalchemy import event, text
from sqlalchemy.engine import Connection, Engine, ExecutionContext
from sqlalchemy.exc import CompileError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ClauseElement
from sqlalchemy.sql.compiler import SQLCompiler

from btrfs_recon import _config
from btrfs_recon.persistence.models import BaseModel
from btrfs_recon.types import ImportItem
from .base import db, pass_session


@db.command()
@click.option(
    "--print-sql",
    is_flag=True,
    default=False,
    help="Echo executed SQL statements to the console",
)
@click.option(
    "--quiet-load",
    is_flag=True,
    default=False,
    help="Don't print list of imported names at shell start",
)
@pass_session
async def shell(session: AsyncSession, print_sql: bool = False, quiet_load: bool = False) -> None:
    """Spawn an IPython shell, already connected to the database, with all models imported"""

    ###
    # IPython uses loop.run_until_complete to execute code from the interactive shell.
    # Unfortunately, because run_until_complete requires the event loop to be stopped
    # when it's called, we run into issues embedding IPython from within an already-running
    # event loop (we use it to initialize an async SQLAlchemy session).
    #
    # To work around this issue, we patch the event loop to allow reentrancy
    # (i.e. invoking run_until_complete from within an existing run_until_complete call).
    #
    # Note that the lack of reentrancy is a design decision: https://bugs.python.org/issue22239
    #
    # Ref: https://github.com/erdewit/nest_asyncio
    #
    nest_asyncio.apply()

    await run_shell(session, print_sql=print_sql, quiet_load=quiet_load)


def import_items(items: Iterable[ImportItem]) -> tuple[dict[str, Any], list[str]]:
    """Import the specified items, returning their values and a list of equivalent import statements

    >>> import_items([
    ...     "collections.abc",
    ...     ("collections", "defaultdict"),
    ...     ("typing", ("dict", "Any")),
    ...     ("btrfs_recon.structure", "*"),
    ... ]) #doctest: +ELLIPSIS +NORMALIZE_WHITESPACE
    ({'collections': <module 'collections' from '.../collections/__init__.py'>,
      'defaultdict': <class 'collections.defaultdict'>,
      'dict': typing.dict,
      'Any': typing.Any},
     ['import collections.abc',
      'from collections import defaultdict',
      'from typing import dict, Any',
      'from btrfs_recon.structure import *'])
    """
    imported_names = {}
    import_statements = []

    for item in items:
        if isinstance(item, str):
            name = item.split(".", maxsplit=1)[0]
            value = __import__(item)
            imported_names[name] = value
            import_statements.append(f"import {item}")

        elif isinstance(item, dict):
            for alias, modname in item.items():
                value = __import__(modname)
                imported_names[alias] = value
                import_statements.append(f"import {modname} as {alias}")

        elif isinstance(item, tuple):
            module_path, fromlist = item
            module = importlib.import_module(module_path)

            if isinstance(fromlist, str):
                if fromlist == "*":
                    if module_all := getattr(module, "__all__", None):
                        fromlist = module_all
                    else:
                        fromlist = [k for k in dir(module) if not k.startswith("_")]

                    import_statements.append(f"from {module_path} import *")

                else:
                    import_statements.append(f"from {module_path} import {fromlist}")
                    fromlist = [fromlist]

            else:
                from_items = []
                for from_item in fromlist:
                    if isinstance(from_item, dict):
                        from_items.extend(f'{attr} as {alias}' for alias, attr in from_item.items())
                    elif isinstance(from_item, str):
                        from_items.append(from_item)
                    else:
                        raise TypeError(f'Unsupported import item: {from_item!r}')

                csv_fromlist = ', '.join(from_items)
                import_statements.append(f"from {module_path} import {csv_fromlist}")

            for from_item in fromlist:
                if isinstance(from_item, str):
                    attr = from_item
                    imported_names[attr] = getattr(module, attr)
                elif isinstance(from_item, dict):
                    for alias, attr in from_item.items():
                        imported_names[alias] = getattr(module, attr)

    return imported_names, import_statements


def get_all_models() -> list[Type[BaseModel]]:
    return [
        mapper.class_
        for mapper in BaseModel._sa_registry.mappers
        if isinstance(mapper.class_, type) and issubclass(mapper.class_, BaseModel)
    ]


async def run_shell(
    session: AsyncSession,
    *,
    print_sql: bool = False,
    quiet_load: bool = False,
    ns: dict[str, Any] = None,
) -> None:
    """Start an IPython session with all models imported and a sqlalchemy session available"""
    imported_names = {}
    import_lines = []

    def import_group(description: str, items: Iterable[ImportItem]) -> None:
        values, lines = import_items(items)
        imported_names.update(values)
        import_lines.append(f"# {description}")
        import_lines.extend(lines)

    def import_models() -> None:
        models_by_module = defaultdict(list)
        for model in get_all_models():
            models_by_module[model.__module__].append(model.__name__)

        import_group("Models", sorted(models_by_module.items(), key=lambda t: t[0]))

    def import_other() -> None:
        import_group("Other Imports", _config.DB_SHELL_EXTRA_IMPORTS)

    import_models()
    import_other()

    other_values = {
        'session': session,
        **(ns or {}),
    }
    import_lines.append("# Other Values")
    import_lines.extend(f"{name}: {type(value).__name__}" for name, value in other_values.items())

    term = TerminalIPythonApp.instance(user_ns={**imported_names, **other_values})
    term.initialize([])

    if not quiet_load:
        shell: TerminalInteractiveShell = term.shell
        import_block = "\n".join(import_lines)
        print(shell.pycolorize(import_block))

    if print_sql:
        install_sqlalchemy_sql_printer()

    term.start()


def install_sqlalchemy_sql_printer() -> None:
    import pygments
    import pygments.formatters
    import pygments.lexers

    try:
        import sqlparse
    except ImportError:
        sqlparse = None

    sql_formatter = pygments.formatters.get_formatter_by_name("terminal")
    sql_lexer = pygments.lexers.get_lexer_by_name("sql")

    compilers_by_bind = {}

    def print_sqla_statement(engine: Engine, statement: ClauseElement) -> None:
        if engine not in compilers_by_bind:
            dialect = engine.dialect
            compiler = statement.compile(dialect=dialect)
            compiler_base: Type[SQLCompiler] = type(compiler)

            class LiteralCompiler(compiler_base):  # type: ignore[valid-type,misc]
                def visit_bindparam(self, bindparam, within_columns_clause=False, literal_binds=False, **kwargs):
                    return super().render_literal_bindparam(
                        bindparam, within_columns_clause=within_columns_clause, literal_binds=literal_binds, **kwargs
                    )

                def render_literal_value(self, value, type_):
                    if value is None:
                        return 'NULL'
                    elif isinstance(value, datetime):
                        return repr(str(value))
                    else:
                        return super().render_literal_value(value, type_)

            compilers_by_bind[engine] = LiteralCompiler(dialect, statement)

        compiler = compilers_by_bind[engine]

        try:
            sql = compiler.process(statement, literal_binds=True)
        except CompileError:
            sql = str(statement)

        if sqlparse:
            sql = sqlparse.format(sql, **_config.DB_SHELL_SQLPARSE_FORMAT_KWARGS)

        sql = pygments.highlight(sql, sql_lexer, sql_formatter)
        print_chunked(sql)

    def build_clause_element(sql: str, parameters: Union[dict, tuple, list]) -> ClauseElement:
        if isinstance(parameters, dict):
            bindparams = parameters
        else:
            bindparams = {f"var{n}": value for n, value in enumerate(parameters)}

        sql = sql % tuple(f":{s}" for s in bindparams)

        parsed_stmt = text(sql)
        return parsed_stmt.bindparams(**bindparams)

    def print_sql_before_cursor_execute(
        conn: Connection,
        cursor,
        statement: str,
        parameters: Union[dict, tuple, list],
        context: Optional[ExecutionContext],
        executemany: bool,
    ):
        clauses: Collection[ClauseElement]
        if executemany:
            clauses = [build_clause_element(statement, values) for values in parameters]
        else:
            clauses = (build_clause_element(statement, parameters),)

        for clause in clauses:
            print_sqla_statement(conn.engine, clause)

        ###
        # Store current time, for use in displaying elapsed execution time
        #
        conn.info["started_at"] = datetime.utcnow()

    def print_elapsed_time_after_cursor_execute(
        conn: Connection,
        cursor,
        statement: str,
        parameters: Union[dict, tuple, list],
        context: Optional[ExecutionContext],
        executemany: bool,
    ) -> None:
        ended_at = datetime.utcnow()
        started_at = conn.info.get("started_at")
        if not started_at:
            return

        elapsed = ended_at - started_at
        elapsed_s = elapsed.total_seconds()

        print(f"Execution time: {elapsed_s}s")
        print()  # spacing

    event.listen(Engine, "before_cursor_execute", print_sql_before_cursor_execute)
    event.listen(Engine, "after_cursor_execute", print_elapsed_time_after_cursor_execute)


def print_chunked(
    *parts, sep: str = " ", end: str = "\n", chunk_size: int = 1024, file=sys.stdout, flush=False
) -> None:
    """print() in chunks to avoid BlockingIOError

    Some SQL queries are massive, and printing them in full results in a BlockingIOError
    being thrown. This method prints in chunks and retries on BlockingIOErrors, ensuring
    the full string prints, if more slowly.

    No delay is placed between successive write attempts in cases of BlockingIOErrors,
    which may incur many wasted CPU cycles.
    """
    buf = sep.join(map(str, parts)) + end
    while buf:
        try:
            n = file.write(buf[:chunk_size])
        except BlockingIOError:
            continue
        buf = buf[n:]
    if flush:
        file.flush()


if __name__ == "__main__":
    shell()
