"""Format error konsisten: {"error": {"code", "message", "details"}}."""
from flask import jsonify
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import HTTPException

from app.extensions import db


class ApiError(Exception):
    def __init__(self, status, code, message, details=None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details


def error_response(status, code, message, details=None):
    body = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return jsonify(body), status


def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def _api_error(e):
        return error_response(e.status, e.code, e.message, e.details)

    @app.errorhandler(IntegrityError)
    def _integrity(e):
        db.session.rollback()
        return error_response(409, "CONFLICT", "Operasi melanggar integritas data (duplikat atau data masih direferensikan).")

    @app.errorhandler(HTTPException)
    def _http(e):
        codes = {400: "BAD_REQUEST", 404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED", 413: "PAYLOAD_TOO_LARGE", 415: "UNSUPPORTED_MEDIA_TYPE"}
        return error_response(e.code, codes.get(e.code, "HTTP_ERROR"), e.description)

    @app.errorhandler(Exception)
    def _unhandled(e):
        db.session.rollback()
        app.logger.exception("Unhandled error")
        # jangan bocorkan detail internal ke klien
        return error_response(500, "INTERNAL_ERROR", "Terjadi kesalahan pada server.")
