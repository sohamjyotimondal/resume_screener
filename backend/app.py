"""
Flask API Example - Resume Processing Service
Shows how to integrate ResumeProcessor with Flask for file uploads
Includes two-level caching:
1. Parsed resume cache (by file hash)
2. Screening result cache (by file hash + job details)
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from main import ResumeProcessor
from cache_manager import CacheManager
import logging
import json

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
logging.basicConfig(level=logging.INFO)

# Initialize the processor and cache manager once at startup
processor = ResumeProcessor()
cache_manager = CacheManager()


@app.route("/api/parse", methods=["POST"])
def parse_resume():
    """
    Parse a resume file with caching.
    Uses file hash to cache parsed resumes and avoid re-parsing.

    Request:
        - file: Resume file (PDF or DOCX)

    Returns:
        JSON with parsed resume data and cache status
    """
    try:
        # Check if file is present
        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files["file"]

        if file.filename == "":
            return jsonify({"error": "No file selected"}), 400

        # Check file extension
        if not file.filename.lower().endswith((".pdf", ".docx", ".doc")):
            return (
                jsonify(
                    {"error": "Invalid file format. Only PDF and DOCX are supported"}
                ),
                400,
            )

        # Read file bytes
        file_bytes = file.read()

        # Generate file hash
        file_hash = cache_manager.hash_file(file_bytes)

        # Check cache for parsed resume
        cached_parsed = cache_manager.get_parsed_resume(file_hash)

        if cached_parsed:
            return (
                jsonify(
                    {
                        "success": True,
                        "data": cached_parsed,
                        "cached": True,
                        "file_hash": file_hash,
                    }
                ),
                200,
            )

        # Parse resume (cache miss)
        parsed = processor.parse_resume_from_bytes(file_bytes, file.filename)

        # Store in cache
        cache_manager.store_parsed_resume(file_hash, parsed)

        return (
            jsonify(
                {
                    "success": True,
                    "data": parsed,
                    "cached": False,
                    "file_hash": file_hash,
                }
            ),
            200,
        )

    except Exception as e:
        logging.error(f"Error parsing resume: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/screen", methods=["POST"])
def screen_resume():
    """
    Screen a resume against job requirements with two-level caching.

    Caching Strategy:
    1. Check if screening result exists (file hash + job details) → return if found
    2. Check if parsed resume exists (file hash only) → use it for screening
    3. Otherwise, parse resume, cache it, then screen it, cache screening result

    Request:
        - file: Resume file (PDF or DOCX)
        - job_title: Job position title
        - job_description: Job description text
        - weights (optional): Custom scoring weights as JSON

    Returns:
        JSON with both parsed and screening results, plus cache status
    """
    try:
        # Check if file is present
        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files["file"]

        if file.filename == "":
            return jsonify({"error": "No file selected"}), 400

        # Check file extension
        if not file.filename.lower().endswith((".pdf", ".docx", ".doc")):
            return (
                jsonify(
                    {"error": "Invalid file format. Only PDF and DOCX are supported"}
                ),
                400,
            )

        # Get job details
        job_title = request.form.get("job_title")
        job_description = request.form.get("job_description")

        if not job_title or not job_description:
            return jsonify({"error": "job_title and job_description are required"}), 400

        # Optional: Custom weights
        weights = None
        if "weights" in request.form:
            weights = json.loads(request.form.get("weights"))

        # Read file bytes
        file_bytes = file.read()

        # Generate file hash
        file_hash = cache_manager.hash_file(file_bytes)

        # LEVEL 1: Check if complete result exists (parsed + screening)
        complete_cached = cache_manager.get_complete_result(
            file_hash, job_title, job_description
        )

        if complete_cached:
            logging.info("✓ Complete cache HIT (both parsed + screened)")
            return (
                jsonify(
                    {
                        "success": True,
                        "data": complete_cached,
                        "cache_status": {
                            "parsed_cached": True,
                            "screening_cached": True,
                            "file_hash": file_hash,
                        },
                    }
                ),
                200,
            )

        # LEVEL 2: Check if parsed resume exists
        cached_parsed = cache_manager.get_parsed_resume(file_hash)

        if cached_parsed:
            logging.info("✓ Parsed resume cache HIT - screening with cached data")

            # Screen using cached parsed data
            screened = processor.screen_resume(
                cached_parsed, job_title, job_description, weights
            )

            # Store screening result in cache
            cache_manager.store_screening_result(
                file_hash, job_title, job_description, screened
            )

            result = {"parsed": cached_parsed, "screened": screened}

            return (
                jsonify(
                    {
                        "success": True,
                        "data": result,
                        "cache_status": {
                            "parsed_cached": True,
                            "screening_cached": False,
                            "file_hash": file_hash,
                        },
                    }
                ),
                200,
            )

        # LEVEL 3: No cache - Parse and screen from scratch
        logging.info("✗ Complete cache MISS - parsing and screening from scratch")

        # Parse resume
        parsed = processor.parse_resume_from_bytes(file_bytes, file.filename)

        # Store parsed resume in cache
        cache_manager.store_parsed_resume(file_hash, parsed)

        # Screen resume
        screened = processor.screen_resume(parsed, job_title, job_description, weights)

        # Store screening result in cache
        cache_manager.store_screening_result(
            file_hash, job_title, job_description, screened
        )

        result = {"parsed": parsed, "screened": screened}

        return (
            jsonify(
                {
                    "success": True,
                    "data": result,
                    "cache_status": {
                        "parsed_cached": False,
                        "screening_cached": False,
                        "file_hash": file_hash,
                    },
                }
            ),
            200,
        )

    except Exception as e:
        logging.error(f"Error screening resume: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "Resume Processing API"}), 200


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
