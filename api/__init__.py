"""Entrypoint for the Pets × AI HTTP API package.

The API package exposes a FastAPI application that serves all HTTP
endpoints defined in the OpenAPI specification under ``contracts/openapi.yaml``.
You can import :data:`api.main.app` to run the server using Uvicorn:

>>> uvicorn api.main:app --reload

The package also exposes some helper functions for dependency injection,
database access and loading deterministic fixtures.
"""

from .main import app  # noqa: F401