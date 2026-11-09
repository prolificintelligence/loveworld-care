"""Bounded keyset pages; current authority is applied by each caller on every request."""

import base64
import json
from uuid import UUID

from sqlalchemy import and_, or_

from .domain import RuleError


def continuation(query, after, order, identifier):
    if after:
        try:
            if len(after) > 4096:
                raise ValueError()
            decoded = json.loads(base64.urlsafe_b64decode(after.encode()).decode())
            if not isinstance(decoded, list) or len(decoded) != 2:
                raise ValueError()
            value, key = decoded
            if not isinstance(value, order.type.python_type) or isinstance(value, bool):
                raise TypeError()
            if len(str(value)) > 512 or not isinstance(key, str) or len(key) > 80:
                raise ValueError()
            if str(UUID(key)) != key or (isinstance(value, str) and "\x00" in value):
                raise ValueError()
            if isinstance(value, int) and not 0 <= value <= 2_147_483_647:
                raise ValueError()
        except (ValueError, TypeError, UnicodeError) as error:
            raise RuleError(
                "INVALID_CURSOR", "Refresh the list to restart pagination", 422
            ) from error
        query = query.where(or_(order > value, and_(order == value, identifier > key)))
    return query.order_by(order, identifier)


async def page(session, query, after, order, identifier, *, size=200):
    rows = list(
        (
            await session.execute(continuation(query, after, order, identifier).limit(size + 1))
        ).mappings()
    )
    cursor = None
    if len(rows) > size:
        last = rows[size - 1]
        cursor = base64.urlsafe_b64encode(
            json.dumps([last[order], last[identifier]], separators=(",", ":")).encode()
        ).decode()
    return rows[:size], cursor
