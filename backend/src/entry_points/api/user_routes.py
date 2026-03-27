"""User management API endpoints — CRUD with soft delete."""

import logging

from flask import Blueprint, g, jsonify, request

from src.entry_points.api.auth_middleware import require_auth, require_role

logger = logging.getLogger(__name__)

user_bp = Blueprint("users", __name__, url_prefix="/api/users")


def _get_user_service():
    from src.container import container
    return container.user_service if container else None


@user_bp.route("", methods=["GET"])
@require_auth
@require_role("admin")
def list_users():
    svc = _get_user_service()
    if not svc:
        return jsonify({"error": "Service not available"}), 503

    include_deleted = request.args.get("include_deleted", "false").lower() == "true"
    try:
        users = svc.list_users(include_deleted=include_deleted)
        return jsonify({"users": users})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@user_bp.route("/roles", methods=["GET"])
@require_auth
@require_role("admin")
def list_roles():
    svc = _get_user_service()
    if not svc:
        return jsonify({"error": "Service not available"}), 503
    try:
        roles = svc.list_roles()
        return jsonify({"roles": roles})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@user_bp.route("", methods=["POST"])
@require_auth
@require_role("admin")
def create_user():
    svc = _get_user_service()
    if not svc:
        return jsonify({"error": "Service not available"}), 503

    data = request.json or {}
    username = data.get("username", "").strip()
    email = data.get("email", "").strip() or None
    password = data.get("password", "")
    role_id = data.get("role_id")

    if not username:
        return jsonify({"error": "Username is required"}), 400
    if not password:
        return jsonify({"error": "Password is required"}), 400
    if not role_id:
        return jsonify({"error": "Role is required"}), 400

    try:
        user = svc.create_user(username, email, password, int(role_id))
        return jsonify({"user": user, "message": f"User '{username}' created"}), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@user_bp.route("/<int:user_id>", methods=["PUT"])
@require_auth
@require_role("admin")
def update_user(user_id: int):
    svc = _get_user_service()
    if not svc:
        return jsonify({"error": "Service not available"}), 503

    data = request.json or {}
    if not data:
        return jsonify({"error": "No data provided"}), 400

    try:
        user = svc.update_user(user_id, data)
        return jsonify({"user": user, "message": "User updated"})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@user_bp.route("/<int:user_id>", methods=["DELETE"])
@require_auth
@require_role("admin")
def delete_user(user_id: int):
    svc = _get_user_service()
    if not svc:
        return jsonify({"error": "Service not available"}), 503

    current_user_id = g.current_user["id"]
    try:
        svc.soft_delete(user_id, current_user_id)
        return jsonify({"message": "User deleted"})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@user_bp.route("/<int:user_id>/restore", methods=["POST"])
@require_auth
@require_role("admin")
def restore_user(user_id: int):
    svc = _get_user_service()
    if not svc:
        return jsonify({"error": "Service not available"}), 503

    try:
        user = svc.restore(user_id)
        return jsonify({"user": user, "message": "User restored"})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@user_bp.route("/<int:user_id>/reset-password", methods=["POST"])
@require_auth
@require_role("admin")
def reset_password(user_id: int):
    svc = _get_user_service()
    if not svc:
        return jsonify({"error": "Service not available"}), 503

    data = request.json or {}
    new_password = data.get("new_password", "")

    if not new_password:
        return jsonify({"error": "New password is required"}), 400

    try:
        svc.admin_reset_password(user_id, new_password)
        return jsonify({"message": "Password reset successfully"})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
