"""Auth API endpoints — login, refresh, logout, password change, user info."""

import logging

from flask import Blueprint, jsonify, request, make_response

from src.entry_points.api.auth_middleware import require_auth

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/api/auth"


def _get_auth_service():
    from src.container import container
    return container.auth_service if container else None


def _set_refresh_cookie(response, raw_token: str, max_age_days: int):
    """Set the httpOnly refresh token cookie."""
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        value=raw_token,
        httponly=True,
        samesite="Strict",
        path=REFRESH_COOKIE_PATH,
        max_age=max_age_days * 86400,
        secure=False,  # Set True when HTTPS is configured
    )


def _clear_refresh_cookie(response):
    """Remove the refresh token cookie."""
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        value="",
        httponly=True,
        samesite="Strict",
        path=REFRESH_COOKIE_PATH,
        max_age=0,
    )


def _safe_user(user: dict) -> dict:
    """Return user info without sensitive fields."""
    return {
        "id": user["id"],
        "username": user["username"],
        "email": user.get("email"),
        "role": user["role_name"],
        "force_password_change": user["force_password_change"],
    }


@auth_bp.route("/login", methods=["POST"])
def login():
    auth_service = _get_auth_service()
    if not auth_service:
        return jsonify({"error": "Service not available"}), 503

    data = request.json or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    try:
        user = auth_service.authenticate(username, password)
    except ValueError as e:
        return jsonify({"error": str(e)}), 401

    access_token = auth_service.create_access_token(user["id"], user["role_name"])
    refresh_token = auth_service.create_refresh_token(user["id"])

    resp = make_response(jsonify({
        "access_token": access_token,
        "user": _safe_user(user),
        "force_password_change": user["force_password_change"],
    }))
    _set_refresh_cookie(resp, refresh_token, auth_service.refresh_token_days)
    return resp


@auth_bp.route("/refresh", methods=["POST"])
def refresh():
    auth_service = _get_auth_service()
    if not auth_service:
        return jsonify({"error": "Service not available"}), 503

    raw_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not raw_token:
        return jsonify({"error": "No refresh token"}), 401

    try:
        new_access, new_refresh = auth_service.refresh_access_token(raw_token)
    except ValueError as e:
        resp = make_response(jsonify({"error": str(e)}), 401)
        _clear_refresh_cookie(resp)
        return resp

    resp = make_response(jsonify({"access_token": new_access}))
    _set_refresh_cookie(resp, new_refresh, auth_service.refresh_token_days)
    return resp


@auth_bp.route("/logout", methods=["POST"])
def logout():
    auth_service = _get_auth_service()
    raw_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if auth_service and raw_token:
        try:
            auth_service.revoke_refresh_token(raw_token)
        except Exception:
            pass

    resp = make_response(jsonify({"message": "Logged out"}))
    _clear_refresh_cookie(resp)
    return resp


@auth_bp.route("/change-password", methods=["POST"])
@require_auth
def change_password():
    from flask import g
    auth_service = _get_auth_service()
    if not auth_service:
        return jsonify({"error": "Service not available"}), 503

    data = request.json or {}
    current = data.get("current_password", "")
    new_pass = data.get("new_password", "")

    if not current or not new_pass:
        return jsonify({"error": "Current and new password are required"}), 400

    try:
        updated_user = auth_service.change_password(g.current_user["id"], current, new_pass)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    # Issue new tokens (old ones were all revoked)
    access_token = auth_service.create_access_token(updated_user["id"], updated_user["role_name"])
    refresh_token = auth_service.create_refresh_token(updated_user["id"])

    resp = make_response(jsonify({
        "message": "Password changed successfully",
        "access_token": access_token,
        "user": _safe_user(updated_user),
    }))
    _set_refresh_cookie(resp, refresh_token, auth_service.refresh_token_days)
    return resp


@auth_bp.route("/me", methods=["GET"])
@require_auth
def me():
    from flask import g
    auth_service = _get_auth_service()
    if not auth_service:
        return jsonify({"error": "Service not available"}), 503

    user = auth_service.get_user(g.current_user["id"])
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({"user": _safe_user(user)})
