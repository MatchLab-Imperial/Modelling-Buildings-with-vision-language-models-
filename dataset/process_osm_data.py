"""
Process OSM data to extract building features and calculate metrics.
"""

import json
from typing import Dict, Any, Optional
import shapely.wkt

from utils import (
    calculate_polygon_area_in_utm,
    convert_osm_to_wkt,
    setup_directory_structure,
)


def load_osm_data(filepath: str) -> Dict[str, Any]:
    """
    Load OSM data from JSON file.

    Args:
        filepath: Path to the OSM data file

    Returns:
        Dict containing the parsed OSM data
    """
    with open(filepath, "r") as f:
        return json.load(f)


def process_osm_building(building: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Process a single building from OSM data, extracting geometry and properties.

    Args:
        building: Dictionary containing OSM building data

    Returns:
        Dictionary with processed OSM building data or None if processing fails
    """
    try:
        # Create WKT string from geometry
        footprint_wkt = convert_osm_to_wkt(building.get("geometry", []))

        # Parse WKT to create polygon
        footprint_polygon = shapely.wkt.loads(footprint_wkt)

        # Get representative point
        representative_point = footprint_polygon.representative_point()
        longitude, latitude = representative_point.x, representative_point.y

        # Calculate area using UTM projection
        footprint_area = calculate_polygon_area_in_utm(footprint_polygon)

        # Extract basic properties
        tags = building.get("tags", {})

        # Set height and levels to None if any error in conversion
        try:
            height = float(tags.get("height"))
        except (ValueError, TypeError):
            height = None

        try:
            levels = int(tags.get("building:levels"))
        except (ValueError, TypeError):
            levels = None

        return {
            "osm_id": building.get("id"),
            "longitude": longitude,
            "latitude": latitude,
            "building_height": height,
            "levels": levels,
            "building_type": tags.get("building", ""),
            "building_material": tags.get("building:material", ""),
            "roof_material": tags.get("roof:material", ""),
            "roof_shape": tags.get("roof:shape", ""),
            "name": tags.get("name", ""),
            "street": tags.get("addr:street", ""),
            "housenumber": tags.get("addr:housenumber", ""),
            "postcode": tags.get("addr:postcode", ""),
            "city": tags.get("addr:city", ""),
            "footprint_wkt": footprint_wkt,
            "footprint_area": footprint_area,  # Area in square metres using UTM projection
        }
    except Exception as e:
        print(f"Error processing building {building.get('id')}: {e}")
        return None


def filter_buildings_by_street(buildings: list, exclude_types: set = None) -> list:
    """
    Filter raw OSM buildings to keep one per street.

    Args:
        buildings: List of raw OSM building dictionaries
        exclude_types: Optional set of building types to exclude (e.g. {"retail", "office"})

    Returns:
        List of buildings with one per street
    """
    seen_streets = set()
    filtered = []
    stats = {
        "total": len(buildings),
        "no_street": 0,
        "duplicate_street": 0,
        "excluded_type": 0,
    }

    # Track building types before filtering
    building_types_before = {}
    for building in buildings:
        if "tags" in building:
            btype = building["tags"].get("building", "unknown")
            building_types_before[btype] = building_types_before.get(btype, 0) + 1

    print("\nBuilding types before filtering:")
    for btype, count in sorted(
        building_types_before.items(), key=lambda x: x[1], reverse=True
    ):
        print(f"{btype}: {count}")

    for building in buildings:
        if "tags" not in building:
            stats["no_tags"] += 1
            continue

        # Check if building type should be excluded
        btype = building["tags"].get("building", "")
        if exclude_types and btype in exclude_types:
            stats["excluded_type"] += 1
            continue

        street = building["tags"].get("addr:street")
        if not street:
            # Keep buildings without street addresses
            stats["no_street"] += 1
            filtered.append(building)
            continue

        if street in seen_streets:
            stats["duplicate_street"] += 1
            continue

        seen_streets.add(street)
        filtered.append(building)

    # Track building types after filtering
    building_types_after = {}
    for building in filtered:
        btype = building["tags"].get("building", "")
        building_types_after[btype] = building_types_after.get(btype, 0) + 1

    print("\nFiltering Stats:")
    print(f"Total buildings: {stats['total']}")
    if exclude_types:
        print(
            f"Buildings with excluded types ({', '.join(sorted(exclude_types))}): {stats['excluded_type']}"
        )
        print(f"Remaining buildings: {stats['total'] - stats['excluded_type']}")
        print(f"- Buildings with no street (kept): {stats['no_street']}")
        print(f"- Buildings removed (duplicate streets): {stats['duplicate_street']}")
        print(
            f"- Buildings kept (unique streets): {len(filtered) - stats['no_street']}"
        )

    print("\nBuilding types after filtering:")
    for btype, count in sorted(
        building_types_after.items(), key=lambda x: x[1], reverse=True
    ):
        print(f"{btype}: {count}")

    return filtered


if __name__ == "__main__":
    # Process OSM data
    input_file = "data/osm/raw.json"
    output_file = "data/osm/processed.json"

    try:
        # Set up directory structure
        setup_directory_structure()

        # Load the OSM data
        osm_data = load_osm_data(input_file)
        raw_buildings = osm_data.get("elements", [])
        print(f"Loaded {len(raw_buildings)} buildings from {input_file}")

        # Filter to one per street
        filtered_buildings = filter_buildings_by_street(
            raw_buildings, exclude_types={"house"}
        )
        print(f"Filtered to {len(filtered_buildings)} buildings (one per street)")

        # Process filtered buildings
        processed_buildings = []
        for building in filtered_buildings:
            processed_building = process_osm_building(building)
            if processed_building:
                processed_buildings.append(processed_building)

        print(f"Successfully processed {len(processed_buildings)} buildings")

        # Save processed data
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(processed_buildings, f, indent=2)

        print(f"\nSaved filtered data to {output_file}")

    except Exception as e:
        print(f"Error: {e}")
