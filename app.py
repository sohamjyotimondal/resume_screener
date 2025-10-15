"""
Flask API Example - Resume Processing Service
Shows how to integrate ResumeProcessor with Flask for file uploads
"""

from flask import Flask, request, jsonify
from main import ResumeProcessor
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Initialize the processor once at startup
processor = ResumeProcessor()


@app.route("/api/parse", methods=["POST"])
def parse_resume():
    """
    Parse a resume file.

    Request:
        - file: Resume file (PDF or DOCX)

    Returns:
        JSON with parsed resume data
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

        # Parse resume
        parsed = processor.parse_resume_from_bytes(file_bytes, file.filename)

        return jsonify({"success": True, "data": parsed}), 200

    except Exception as e:
        logging.error(f"Error parsing resume: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/screen", methods=["POST"])
def screen_resume():
    """
    Screen a resume against job requirements.

    Request:
        - file: Resume file (PDF or DOCX)
        - job_title: Job position title
        - job_description: Job description text
        - weights (optional): Custom scoring weights as JSON

    Returns:
        JSON with both parsed and screening results
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
            import json

            weights = json.loads(request.form.get("weights"))

        # Read file bytes
        file_bytes = file.read()

        # Process resume (parse + screen)
        result = processor.process_resume_from_bytes(
            file_bytes, file.filename, job_title, job_description, weights
        )

        return jsonify({"success": True, "data": result}), 200

    except Exception as e:
        logging.error(f"Error screening resume: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "Resume Processing API"}), 200


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
