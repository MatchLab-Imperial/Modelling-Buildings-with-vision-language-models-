"""
Module for fetching and processing OpenStreetMap data using the Overpass API.

This module provides functionality to query the Overpass API for building data
in the UK and save the results locally for further processing.
"""

import json
import argparse
import requests
from pathlib import Path
from typing import Dict, Any, Optional
from utils import setup_directory_structure


def create_overpass_query(num_buildings: Optional[int] = None) -> str:
    """
    Create an Overpass query for fetching building data in Great Britain.
    Bounding box covers England, Wales, and most of Scotland
    (49.8°N to 58.7°N, 5.8°W to 1.8°E).

    Args:
        num_buildings: Optional number of buildings to fetch. If None, fetches all matches.

    Returns:
        str: The formatted Overpass query
    """
    query = """[out:json][timeout:500];
// Gather ways that are buildings with required attributes
way
  ["building"~"^(commercial|retail|office|apartments|residential|house|detached|terrace|semidetached_house)$"]
  ["height"]
  ["building:levels"]
  ["building:material"]
//  ["roof:material"]
//  ["roof:shape"]
//  ["addr:street"]
//  ["name"]
  (49.8,-5.8,58.7,1.8);"""

    # Add limit only if num_buildings is specified
    if num_buildings:
        query += f"\nout body geom {num_buildings};"
    else:
        query += "\nout body geom;"

    return query


def fetch_osm_data(query: str) -> Dict[str, Any]:
    """
    Fetch building data from OpenStreetMap using the Overpass API.

    Args:
        query: The Overpass query string to execute

    Returns:
        Dict containing the JSON response from the Overpass API with building geometries

    Raises:
        requests.RequestException: If the API request fails
    """
    overpass_url = "https://overpass-api.de/api/interpreter"
    response = requests.post(overpass_url, data={"data": query})
    response.raise_for_status()
    return response.json()


def save_osm_data(data: Dict[str, Any], output_dir: str) -> str:
    """
    Save the OSM data to a JSON file.

    Args:
        data: Dictionary containing the OSM data with geometries
        output_dir: Directory to save the data

    Returns:
        str: Path to the saved file
    """
    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Save as raw.json in the osm directory
    filepath = output_path / "raw.json"

    # Save the data
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    return str(filepath)


def parse_args() -> argparse.Namespace:
    """
    Parse command line arguments.

    Returns:
        Namespace containing the parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Fetch building data from OpenStreetMap using the Overpass API"
    )
    parser.add_argument(
        "-n",
        "--num-buildings",
        type=int,
        help="Optional: number of buildings to fetch. If not specified, fetches all matches.",
        required=False,
        default=None,
    )
    return parser.parse_args()


if __name__ == "__main__":
    try:
        # Set up directory structure
        setup_directory_structure()

        # Parse command line arguments
        args = parse_args()

        # Create the query
        if args.num_buildings is not None:
            print(f"Fetching {args.num_buildings} buildings from OpenStreetMap...")
            query = create_overpass_query(args.num_buildings)
        else:
            print("Fetching all buildings from OpenStreetMap...")
            query = create_overpass_query()

        # Fetch the data
        osm_data = fetch_osm_data(query)

        # Save the data
        output_dir = "data/osm"
        saved_file = save_osm_data(osm_data, output_dir)
        print(f"\nData successfully saved to: {saved_file}")
        print(f"Number of buildings fetched: {len(osm_data.get('elements', []))}")

    except requests.RequestException as e:
        print(f"Error fetching data: {e}")
    except Exception as e:
        print(f"Error: {e}")
