"""
Utility functions for geometry calculations and Street View image handling.
"""

import os
from typing import Tuple, Optional
import numpy as np
from numpy.linalg import norm
import yaml
import json
from pyproj import Transformer
import utm
import requests
from shapely.geometry import Polygon, LinearRing
from dotenv import load_dotenv
import base64

# Load environment variables
load_dotenv()
GOOGLE_MAPS_KEY = os.getenv("GOOGLE_MAPS_KEY")
DEFAULT_PITCH_ANGLE = 30

# Initialise transformer for geocentric calculations
latlong_geocent_transformer = Transformer.from_crs(
    "EPSG:4326", "EPSG:4978", always_xy=True
)


def calculate_ring_area_in_utm(ring: LinearRing) -> float:
    """
    Calculate the area of a ring (exterior or interior) by converting to UTM coordinates.

    Args:
        ring: Shapely LinearRing in lat/lon coordinates

    Returns:
        float: Area in square metres
    """
    polygon_utm = []
    for vertex in ring.coords:
        easting, northing, _, _ = utm.from_latlon(vertex[1], vertex[0])
        polygon_utm.append((easting, northing))
    return Polygon(polygon_utm).area


def calculate_polygon_area_in_utm(polygon: Polygon) -> float:
    """
    Calculate the area of a polygon in square metres by converting to UTM coordinates.
    Handles polygons with holes by subtracting the hole areas.

    Args:
        polygon: Shapely Polygon in lat/lon coordinates

    Returns:
        float: Area in square metres
    """
    area = calculate_ring_area_in_utm(polygon.exterior)
    for hole in polygon.interiors:
        area -= calculate_ring_area_in_utm(hole)
    return area


def convert_osm_to_wkt(geometry: list) -> str:
    """
    Convert OSM geometry to WKT format.

    Args:
        geometry: List of OSM nodes with lon/lat coordinates

    Returns:
        WKT string representing the polygon
    """
    coords = [(node["lon"], node["lat"]) for node in geometry]
    # Close the polygon if it's not already closed
    if coords[0] != coords[-1]:
        coords.append(coords[0])
    coord_str = ", ".join(f"{lon} {lat}" for lon, lat in coords)
    return f"POLYGON(({coord_str}))"


def get_streetview_metadata_url(longitude: float, latitude: float) -> str:
    """
    Create URL for Street View metadata API.

    Args:
        longitude: Longitude of the point
        latitude: Latitude of the point

    Returns:
        str: URL for the Street View metadata API
    """
    return f"https://maps.googleapis.com/maps/api/streetview/metadata?location={latitude},{longitude}&source=outdoor&key={GOOGLE_MAPS_KEY}"


def get_streetview_camera_position(
    longitude: float, latitude: float
) -> Optional[Tuple[float, float]]:
    """
    Check if Street View is available at the given coordinates and get the actual
    Street View camera position.

    Args:
        longitude: Longitude to check
        latitude: Latitude to check

    Returns:
        Tuple of (longitude, latitude) if Street View is available, None otherwise
    """
    url = get_streetview_metadata_url(longitude, latitude)
    res = requests.get(url)
    if res.status_code == 200:
        meta_data = res.json()
        status = meta_data.get("status")
        if status == "OK":
            location = meta_data.get("location")
            camera_position = (location.get("lng"), location.get("lat"))
            return camera_position
    return None


def get_streetview_url(
    longitude: float,
    latitude: float,
    building_height: float = None,
    use_building_height: bool = False,
    pitch: float = DEFAULT_PITCH_ANGLE,
) -> Optional[str]:
    """
    Create URL for Street View image API.

    Args:
        longitude: Longitude of the point
        latitude: Latitude of the point
        building_height: Building height in metres (optional)
        use_building_height: Whether to calculate pitch based on building height
        pitch: Camera pitch angle in degrees (default: 30, only used if use_building_height is False)

    Returns:
        str: URL for the Street View image API
    """
    if use_building_height and building_height:
        poly_center = latlong_geocent_transformer.transform(longitude, latitude, 0)
        streetview_coords = get_streetview_camera_position(longitude, latitude)
        if streetview_coords:
            origin = latlong_geocent_transformer.transform(*streetview_coords, 0)
            vec0 = np.array(poly_center) - np.array(origin)
            vec1 = np.array(
                latlong_geocent_transformer.transform(
                    longitude, latitude, building_height
                )
            ) - np.array(origin)
            cosine = np.dot(vec0, vec1) / (norm(vec0) * norm(vec1))
            pitch = np.degrees(np.arccos(cosine)) * 0.5

    return f"https://maps.googleapis.com/maps/api/streetview?size=350x350&location={latitude},{longitude}&fov=70&pitch={pitch}&source=outdoor&key={GOOGLE_MAPS_KEY}"


def download_streetview_image(
    longitude: float,
    latitude: float,
    output_path: str,
    building_height: float = None,
    use_building_height: bool = False,
    pitch: float = DEFAULT_PITCH_ANGLE,
) -> bool:
    """
    Download a Street View image for a given location.

    Args:
        longitude: Longitude of the point
        latitude: Latitude of the point
        output_path: Path to save the image
        building_height: Building height in metres (optional)
        use_building_height: Whether to calculate pitch based on building height
        pitch: Camera pitch angle in degrees (default: 30, only used if use_building_height is False)

    Returns:
        bool: True if image was downloaded successfully, False otherwise
    """
    # Get Street View URL
    url = get_streetview_url(
        longitude,
        latitude,
        building_height=building_height,
        use_building_height=use_building_height,
        pitch=pitch,
    )

    if not url:
        return False

    try:
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Download the image
        response = requests.get(url)
        response.raise_for_status()

        # Check if we got an actual image (Street View API returns a blank image if no photo exists)
        if len(response.content) < 5000:  # Blank images are typically very small
            return False

        # Save the image
        with open(output_path, "wb") as f:
            f.write(response.content)
        return True

    except Exception as e:
        print(f"Error downloading image: {e}")
        return False


def setup_directory_structure() -> None:
    """
    Create the project's directory structure if it doesn't exist.
    This includes directories for OSM data, images, and logs.
    """
    directories = [
        "data/osm",
        "data/images/fixed_pitch",
        "data/images/height_pitch",
        "data/logs",
    ]

    for directory in directories:
        os.makedirs(directory, exist_ok=True)


def load_yaml_to_json(yaml_file_path):
    """
    Load YAML file into JSON formatted string.

    Args:
        yaml_file (str): name of YAML file.

    Returns:
        str: JSON formatted string.
    """
    # Read the YAML file
    with open(yaml_file_path, "r") as file:
        yaml_content = yaml.safe_load(file)

    # Convert the dictionary to a JSON string
    json_output = json.dumps(yaml_content, indent=4)
    return json_output


def base64_encode_image(image_bytes):
    """
    Encode an image in bytes to base64.

    Args:
        image_bytes (str): image in bytes.

    Returns:
        str: base64 encoded image.
    """
    # Encode the image bytes into base64
    encoded_image = base64.b64encode(image_bytes)

    # Convert base64 bytes to a string, if needed
    encoded_image_str = encoded_image.decode("utf-8")

    return encoded_image_str


def load_and_encode_all_images(image_paths):
    """
    Load images stored locally and encode into base64, appending all to a list.

    Args:
        image_paths (List[str]): paths to images.

    Returns:
        List[str]: list of base64 encoded images.
    """
    all_encoded_images = []

    for image_path in image_paths:
        with open(image_path, "rb") as f:
            image_bytes = f.read()
            encoded_image = base64_encode_image(image_bytes)

        all_encoded_images.append(encoded_image)
    return all_encoded_images


def format_image_for_model(base64_image: str, model: str) -> dict:
    """
    Format a base64 encoded image for different model providers.

    Args:
        base64_image: Base64 encoded image string
        model: Model identifier (starting with 'gemini', 'gpt', or 'claude')

    Returns:
        dict: Properly formatted image object for the specified model
    """
    if model.startswith("gemini"):
        return {
            "type": "image_url",
            "image_url": f"data:image/jpeg;base64,{base64_image}",
        }
    elif model.startswith("gpt"):
        return {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
        }
    elif model.startswith("claude"):
        return {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
        }
    else:
        raise ValueError(f"Unsupported model type: {model}")
