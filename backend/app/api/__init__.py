"""FastAPI routers. Thin by contract: HTTP concerns and nothing else.

A router never imports a model or opens a session, and never raises
``HTTPException`` on behalf of a domain rule — the service raises a typed domain
exception and the error handler maps it.
"""
