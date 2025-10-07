import os
import math
import requests
from urllib.parse import urlencode

# Google Static Maps API endpoint
_STATIC_MAPS_ENDPOINT = "https://maps.googleapis.com/maps/api/staticmap"

def meters_per_pixel(lat_deg: float, zoom: int, scale: int = 1) -> float:
    """
    Estimate ground resolution (meters per pixel).
    Useful for choosing an appropriate zoom level and scale.
    """
    earth_circumference = 40075016.686  # meters
    return (math.cos(math.radians(lat_deg)) * earth_circumference) / (256 * (2 ** zoom) * scale)

def fetch_google_aerial(
    lat: float,
    lon: float,
    *,
    zoom: int = 19,
    size: str = "640x640",
    scale: int = 2,
    fmt: str = "png",          # "png", "jpg", or "webp"
    marker: str | None = None, # Example: "color:red|40.6892,-74.0445"
    api_key: str | None = None,
    outfile: str | None = None,
    timeout: int = 60,
) -> bytes | str:
    """
    Fetch a Google Maps satellite (aerial) image centered at a given latitude and longitude.

    Parameters:
        lat, lon: Coordinates of the target location.
        zoom: Zoom level (0 = world view, up to ~21 for street-level).
        size: Image size as "widthxheight" (max 640x640 per API limits).
               If scale=2, resolution doubles (e.g., 1280x1280 effective).
        scale: 1 (standard) or 2 (high resolution).
        fmt: Output image format ("png", "jpg", or "webp").
        marker: Optional marker string, e.g., "color:red|{lat},{lon}".
        api_key: Google Maps API key; if None, reads from environment variable GOOGLE_MAPS_API_KEY.
        outfile: If specified, saves the image to a file and returns the filename.
                 Otherwise returns raw image bytes.
        timeout: HTTP request timeout (seconds).

    Returns:
        bytes if outfile is None, otherwise a file path (str).

    Notes:
        - "maptype=satellite" gives an aerial (orthographic) view.
        - For roads and labels overlaid, use "maptype=hybrid".
        - The static API supports only north-up orthographic images, no tilt control.
    """
    key = api_key or os.environ.get("GOOGLE_MAPS_API_KEY")
    if not key:
        raise ValueError("Missing API key: provide api_key or set GOOGLE_MAPS_API_KEY env variable.")

    params = {
        "center": f"{lat},{lon}",
        "zoom": str(zoom),
        "size": size,
        "scale": str(scale),
        "maptype": "satellite",
        "format": fmt,
        "key": key,
    }
    if marker:
        params["markers"] = marker

    url = f"{_STATIC_MAPS_ENDPOINT}?{urlencode(params, safe=',|:')}"
    response = requests.get(url, timeout=timeout)

    # The API may return an error as text or an image with an error message
    if response.status_code != 200 or response.headers.get("Content-Type", "").startswith("text/"):
        raise RuntimeError(f"Request failed (status={response.status_code}): {response.text[:200]}")

    if outfile:
        with open(outfile, "wb") as f:
            f.write(response.content)
        print(f"✅ Saved to {outfile}")
        return outfile
    else:
        return response.content


# ---------- Example usage ----------
# Before running, ensure your environment variable is set:
#   export GOOGLE_MAPS_API_KEY="YOUR_API_KEY"

if True:  # just to make the example run safely in any context
    image_path = fetch_google_aerial(
        lat=40.6892,          # Example: Statue of Liberty
        lon=-74.0445,
        zoom=19,
        size="640x640",
        scale=2,
        outfile="liberty_aerial.png"
    )
    print(f"Image saved at: {image_path}")
    print("Approx. ground resolution:",
          f"{meters_per_pixel(40.6892, 19, 2):.2f} meters/pixel")
