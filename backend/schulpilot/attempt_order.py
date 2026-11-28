"""Order attempts of one question using their persisted sequence number."""

from sqlalchemy import Boolean, Integer
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.functions import FunctionElement


class valid_attempt_number(FunctionElement):
    """Return a bounded positive JSON integer, or SQL NULL for legacy junk.

    Never cast untrusted JSON text before checking its type and range: PostgreSQL
    otherwise aborts the transaction on strings, fractions or huge integers.
    """

    type = Integer()
    inherit_cache = True


class conservative_independence_uncertain(FunctionElement):
    """Invalid non-null independence metadata must not assert independence."""

    type = Boolean()
    inherit_cache = True


@compiles(valid_attempt_number, "postgresql")
def _postgres_number(element, compiler, **kw):
    column = compiler.process(next(iter(element.clauses)), **kw)
    value = f"({column} ->> 'attempt_number')"
    return (f"CASE WHEN json_typeof({column} -> 'attempt_number') = 'number' "
            f"AND {value} ~ '^[1-9][0-9]{{0,8}}$' "
            f"THEN CAST({value} AS INTEGER) ELSE NULL END")


@compiles(valid_attempt_number, "sqlite")
def _sqlite_number(element, compiler, **kw):
    column = compiler.process(next(iter(element.clauses)), **kw)
    value = f"json_extract({column}, '$.attempt_number')"
    return (f"CASE WHEN json_type({column}, '$.attempt_number') = 'integer' "
            f"AND {value} BETWEEN 1 AND 999999999 THEN {value} ELSE NULL END")


@compiles(conservative_independence_uncertain, "postgresql")
def _postgres_uncertain(element, compiler, **kw):
    column = compiler.process(next(iter(element.clauses)), **kw)
    kind = f"json_typeof({column} -> 'independence_uncertain')"
    return (f"CASE WHEN {kind} IS NULL OR {kind} = 'null' THEN FALSE "
            f"WHEN {kind} = 'boolean' THEN ({column} ->> 'independence_uncertain') = 'true' ELSE TRUE END")


@compiles(conservative_independence_uncertain, "sqlite")
def _sqlite_uncertain(element, compiler, **kw):
    column = compiler.process(next(iter(element.clauses)), **kw)
    kind = f"json_type({column}, '$.independence_uncertain')"
    return (f"CASE WHEN {kind} IS NULL OR {kind} IN ('null', 'false') THEN 0 ELSE 1 END")


def question_order(attempt):
    evaluation = attempt.evaluation if isinstance(attempt.evaluation, dict) else {}
    number = evaluation.get("attempt_number")
    return attempt.created, number if type(number) is int and 1 <= number <= 999999999 else 0, attempt.id
