from flask import Blueprint, request, jsonify
from datetime import datetime
from .utils import get_routes_from_openrouteservice

bp = Blueprint("routes", __name__)

@bp.route("/")
def home():
    """
    Root endpoint to confirm API is running.
    """
    return jsonify({"message": "Welcome to the Route Recommendation API!"})


@bp.route("/routes", methods=["GET"])
def get_routes():
    """
    Fetch recommended routes between source and destination.
    Query Parameters:
        - source: Starting location (string or coordinates)
        - destination: Destination location (string or coordinates)
        - departure: Optional departure datetime in ISO format (e.g. 2025-07-14T17:00)
    Returns:
        JSON with route alternatives and scoring metrics.
    """
    source = request.args.get("source")
    destination = request.args.get("destination")
    departure = request.args.get("departure")

    if not source or not destination:
        return jsonify({"error": "Both 'source' and 'destination' parameters are required"}), 400

    departure_time = None
    if departure:
        try:
            departure_time = datetime.fromisoformat(departure)
        except ValueError:
            return jsonify({
                "error": "Invalid departure format. Use ISO format like 2025-07-14T17:00"
            }), 400

    try:
        routes = get_routes_from_openrouteservice(source, destination, departure_time)
        return jsonify({"routes": routes})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
