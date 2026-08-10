"""Minimal web front-end: upload files -> get back one compressed PDF.

Every setting lives in config.py.
"""

from __future__ import annotations

import argparse
import io

from flask import Flask, jsonify, render_template, request, send_file

import config
from pdf_tools import (
    ProcessingError,
    build_pdf,
    dpi_slider,
    supported_extensions,
)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = config.MAX_UPLOAD_MB * 1024 * 1024


def _ascii(value: str) -> str:
    """HTTP headers are latin-1 only; keep them boring."""
    return value.encode("ascii", "replace").decode("ascii")


@app.get("/")
def index():
    return render_template(
        "index.html",
        max_upload_mb=config.MAX_UPLOAD_MB,
        max_files=config.MAX_FILES,
        page_size=config.PAGE_SIZE.upper(),
        slider=dpi_slider(),
        accept=",".join(sorted(supported_extensions())),
    )


@app.post("/process")
def process():
    uploads = [f for f in request.files.getlist("files") if f.filename]
    if not uploads:
        return jsonify(error="No files were uploaded."), 400
    if len(uploads) > config.MAX_FILES:
        return jsonify(error=f"Too many files at once (limit {config.MAX_FILES})."), 400

    def stream():
        """Hand the pipeline one upload at a time: werkzeug has already spooled
        the big ones to disk, so reading them all up front would be the single
        largest thing in memory."""
        for upload in uploads:
            yield upload.filename, upload.read()

    try:
        result = build_pdf(stream(), dpi=request.form.get("dpi"))
    except ProcessingError as exc:
        return jsonify(error=str(exc)), 400
    except Exception:  # noqa: BLE001 - never leak a stack trace to the browser
        app.logger.exception("processing failed")
        return jsonify(error="Something went wrong while building the PDF."), 500

    response = send_file(
        io.BytesIO(result.data),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=result.filename,
    )
    response.headers["X-Original-Bytes"] = str(result.original_bytes)
    response.headers["X-Output-Bytes"] = str(len(result.data))
    response.headers["X-Pages"] = str(result.pages)
    response.headers["X-Dpi"] = str(result.quality.target_dpi)
    response.headers["X-Notes"] = _ascii(" | ".join(result.notes))
    response.headers["Access-Control-Expose-Headers"] = (
        "X-Original-Bytes, X-Output-Bytes, X-Pages, X-Dpi, X-Notes, "
        "Content-Disposition"
    )
    return response


@app.errorhandler(413)
def too_large(_exc):
    return jsonify(error=f"Upload is larger than {config.MAX_UPLOAD_MB} MB."), 413


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Command-line options. Values from config.py are the defaults."""
    parser = argparse.ArgumentParser(description="pdf-tools: upload files, get one compressed PDF")
    parser.add_argument("--port", "-p", type=int, default=config.PORT,
                        help=f"port to listen on (default {config.PORT})")
    parser.add_argument("--host", default=config.HOST,
                        help=f"address to bind (default {config.HOST}; 0.0.0.0 for the network)")
    parser.add_argument("--debug", action="store_true", default=config.DEBUG,
                        help="enable the Flask debugger and reloader")
    return parser.parse_args(argv)


if __name__ == "__main__":
    options = parse_args()
    app.run(host=options.host, port=options.port, debug=options.debug)
