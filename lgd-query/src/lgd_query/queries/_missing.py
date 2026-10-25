"""Explicit NULL/empty-string predicates over allowlisted report columns."""

from collections.abc import Sequence

Columns = str | Sequence[str] | None


def column_names(value: Columns, option: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        value = (value,)
    if not isinstance(value, Sequence) or any(not isinstance(v, str) for v in value):
        raise ValueError(f'{option} must be a column name or a sequence of column names')
    return tuple(dict.fromkeys(value))


def missing_conditions(columns, *, alias, nontext=(), is_null=None, is_blank=None):
    nulls = column_names(is_null, 'is_null')
    blanks = column_names(is_blank, 'is_blank')
    unknown = (set(nulls) | set(blanks)) - set(columns)
    if unknown:
        raise ValueError(f'Unknown missing-value column(s): {", ".join(sorted(unknown))}')
    invalid = set(blanks) & set(nontext)
    if invalid:
        raise ValueError(f'is_blank requires text columns: {", ".join(sorted(invalid))}')
    if set(nulls) & set(blanks):
        raise ValueError('A column cannot be both is_null and is_blank')
    return [*(f'{alias}.{c} IS NULL' for c in nulls),
            *(f"{alias}.{c} = ''" for c in blanks)]
