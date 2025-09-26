"""
Test script to check Street View camera positions.
"""

from utils import get_streetview_camera_position
from dotenv import load_dotenv
import sys

load_dotenv()


def test_camera_position(longitude: float, latitude: float):
    """Test getting camera position for a given location."""
    result = get_streetview_camera_position(longitude, latitude)

    if result:
        camera_lon, camera_lat = result
        print("Camera position found")
        print(f"  Requested: {latitude}, {longitude}")
        print(f"  Camera:   {camera_lat}, {camera_lon}")
    else:
        print("No Street View available")


if __name__ == "__main__":
    if len(sys.argv) == 3:
        try:
            lon = float(sys.argv[1])
            lat = float(sys.argv[2])
            test_camera_position(lon, lat)
        except ValueError:
            print("Provide valid longitude and latitude as floats")
    else:
        print("Usage: python test_camera_position.py <longitude> <latitude>")
