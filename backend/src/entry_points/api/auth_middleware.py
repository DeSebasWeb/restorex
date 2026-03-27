"""JWT authentication and role-based authorization decorators."""

import functools
import logging

import jwt
from flask import g, jsonify, request

logger = logging.getLogger(__name__)

# Role hierarchy: higher number = more permissions
ROLE_HIERARCHY = {"admin": 3, "operator": 2, "viewer": 1}


def _get_auth_service():
    """Lazy access to the auth service from the global container."""
    from src.container import container
    if container is None:
        return None
    return container.auth_service


def require_auth(fn):
    """Decorator: validates JWT access token and sets g.current_user."""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Authentication required"}), 401

        token = auth_header[7:]  # Strip "Bearer "
        auth_service = _get_auth_service()
        if not auth_service:
            return jsonify({"error": "Auth service not available"}), 503

        try:
            payload = auth_service.verify_access_token(token)
            g.current_user = {
                "id": payload["sub"],
                "role": payload["role"],
            }
            return fn(*args, **kwargs)
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired", "code": "TOKEN_EXPIRED"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

    return wrapper


def require_role(*allowed_roles):
    """Decorator factory: checks if user's role meets minimum required level.

    Uses hierarchy: admin > operator > viewer.
    A higher role automatically has access to lower-role endpoints.
    Must be used after @require_auth.

    Usage:
        @require_auth
        @require_role("operator")
        def my_endpoint():
            ...
    """

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if not hasattr(g, 'current_user'):
                return jsonify({"error": "Authentication required"}), 401
            user_role = g.current_user.get("role", "")
            user_level = ROLE_HIERARCHY.get(user_role, 0)
            min_level = min(ROLE_HIERARCHY.get(r, 99) for r in allowed_roles)

            if user_level >= min_level:
                return fn(*args, **kwargs)

            return jsonify({"error": "Insufficient permissions"}), 403

        return wrapper

    return decorator
