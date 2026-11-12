"""Reading a CSV file sent as the request body (SPEC-0003 AC-0003-18).

The file is the body itself, `Content-Type: text/csv`, rather than
`multipart/form-data`, which FastAPI reads only through a dependency it does not
install. The body ceiling for these routes is applied before this runs
(AC-0001-42 v1.10).
"""

from __future__ import annotations

from fastapi import Request


async def csv_body(request: Request) -> bytes:
    """The raw bytes of the uploaded file."""
    return await request.body()
