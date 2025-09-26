"""
Download Street View images for processed buildings.
"""

import json
import logging
import argparse
import time
from typing import Dict, Any
from utils import download_streetview_image, setup_directory_structure
import os.path


def configure_logging(log_directory: str) -> None:
    """
    Set up logging configuration.

    Args:
        log_directory: Directory to store log files
    """
    log_file = f"{log_directory}/streetview.log"

    # Create formatter
    formatter = logging.Formatter("%(asctime)s - %(message)s")

    # Set up file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)

    # Configure logger
    logger = logging.getLogger("streetview_download")
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)


def download_building_images(
    building_data: Dict[str, Any],
    image_directory: str,
    fetch_fixed_pitch: bool = True,
    fetch_height_pitch: bool = True,
    fixed_pitch: float = 30.0,
) -> Dict[str, Any]:
    """
    Download Street View images for a building using selected pitch options.
    Skips download if image already exists.

    Args:
        building_data: Dictionary containing building data
        image_directory: Base directory for saving images
        fetch_fixed_pitch: Whether to fetch image with fixed pitch
        fetch_height_pitch: Whether to fetch image with height-based pitch
        fixed_pitch: Angle in degrees for fixed pitch image (default: 30.0)

    Returns:
        Updated building dictionary with image paths
    """
    osm_id = building_data["osm_id"]
    logger = logging.getLogger("streetview_download")
    logger.info(f"Processing building (OSM ID: {osm_id})")

    # Initialise image paths to None
    building_data["fixed_pitch_image"] = None
    building_data["height_pitch_image"] = None

    # 1. Fixed pitch
    if fetch_fixed_pitch:
        fixed_pitch_image_path = f"{image_directory}/fixed_pitch/{osm_id}.jpg"
        if os.path.exists(fixed_pitch_image_path):
            building_data["fixed_pitch_image"] = fixed_pitch_image_path
            logger.info(
                f"Skipped download - fixed pitch image already exists ({fixed_pitch}°)"
            )
        elif download_streetview_image(
            building_data["longitude"],
            building_data["latitude"],
            fixed_pitch_image_path,
            building_height=building_data["building_height"],
            use_building_height=False,
            pitch=fixed_pitch,
        ):
            building_data["fixed_pitch_image"] = fixed_pitch_image_path
            logger.info(f"Downloaded fixed pitch image ({fixed_pitch}°)")
        else:
            logger.warning(f"Failed to download fixed pitch image ({fixed_pitch}°)")

    # 2. Height-based pitch
    if fetch_height_pitch:
        height_pitch_image_path = f"{image_directory}/height_pitch/{osm_id}.jpg"
        if os.path.exists(height_pitch_image_path):
            building_data["height_pitch_image"] = height_pitch_image_path
            logger.info("Skipped download - height-based pitch image already exists")
        elif download_streetview_image(
            building_data["longitude"],
            building_data["latitude"],
            height_pitch_image_path,
            building_height=building_data["building_height"],
            use_building_height=True,
        ):
            building_data["height_pitch_image"] = height_pitch_image_path
            logger.info("Downloaded height-based pitch image")
        else:
            logger.warning("Failed to download height-based pitch image")

    return building_data


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Download Street View images for buildings"
    )
    parser.add_argument(
        "--fixed-pitch", action="store_true", help="Fetch images with fixed pitch"
    )
    parser.add_argument(
        "--height-pitch",
        action="store_true",
        help="Fetch images with height-based pitch",
    )
    parser.add_argument(
        "--pitch",
        type=float,
        default=30.0,
        help="Angle in degrees for fixed pitch images (default: 30.0)",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.1,
        help="Sleep time between requests in seconds (default: 0.1)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of buildings to process (for testing)",
    )
    args = parser.parse_args()

    # If neither specified, default to fixed pitch
    if not args.fixed_pitch and not args.height_pitch:
        args.fixed_pitch = True

    # Download Street View images for processed buildings
    input_file = "data/osm/processed.json"
    output_file = "data/osm/processed_with_images.json"
    image_directory = "data/images"
    log_directory = "data/logs"

    try:
        # Set up directory structure
        setup_directory_structure()

        # Set up logging
        configure_logging(log_directory)
        logger = logging.getLogger("streetview_download")
        logger.info("Starting Street View image download process")
        if args.fixed_pitch:
            logger.info(f"Will fetch fixed pitch images at {args.pitch}°")
        if args.height_pitch:
            logger.info("Will fetch height-based pitch images")
        logger.info(f"Sleep time between requests: {args.sleep}s")
        if args.limit:
            logger.info(f"Testing mode: processing first {args.limit} buildings only")

        # Load processed building data
        with open(input_file, "r") as f:
            buildings = json.load(f)
            buildings_to_process = buildings[: args.limit] if args.limit else buildings
        logger.info(
            f"Processing {len(buildings_to_process)} out of {len(buildings)} buildings"
        )

        # Load existing buildings with images
        existing_buildings = {}
        if os.path.exists(output_file):
            with open(output_file, "r") as f:
                for building in json.load(f):
                    existing_buildings[building["osm_id"]] = building
            logger.info(
                f"Loaded {len(existing_buildings)} existing buildings with images"
            )

        skipped_downloads = 0
        for building in buildings_to_process:
            building_with_images = download_building_images(
                building,
                image_directory,
                fetch_fixed_pitch=args.fixed_pitch,
                fetch_height_pitch=args.height_pitch,
                fixed_pitch=args.pitch,
            )
            # Only keep buildings that have at least one successful image download
            if (
                building_with_images["fixed_pitch_image"]
                or building_with_images["height_pitch_image"]
            ):
                existing_buildings[building_with_images["osm_id"]] = (
                    building_with_images
                )
            else:
                skipped_downloads += 1
            time.sleep(args.sleep)

        logger.info(
            f"Successfully downloaded images for {len(existing_buildings)} buildings"
        )
        logger.info(f"Skipped {skipped_downloads} downloads due to existing images")

        # Save updated data
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(list(existing_buildings.values()), f, indent=2)
        logger.info(f"Saved updated data to {output_file}")

        # Print summary
        fixed_pitch_image_count = sum(
            1 for b in existing_buildings.values() if b["fixed_pitch_image"]
        )
        height_pitch_image_count = sum(
            1 for b in existing_buildings.values() if b["height_pitch_image"]
        )
        print("\nProcessing Summary:")
        print(f"Total buildings processed: {len(existing_buildings)}")
        print("Street View images downloaded:")
        print(f"  - Fixed pitch ({args.pitch}°): {fixed_pitch_image_count}")
        print(f"  - Height-based pitch: {height_pitch_image_count}")
        print(f"Skipped downloads due to existing images: {skipped_downloads}")
        print("\nDetailed download information saved to data/logs/streetview.log")

    except Exception as e:
        print(f"Error: {e}")
        logger = logging.getLogger("streetview_download")
        logger.error(f"Error during processing: {e}")
