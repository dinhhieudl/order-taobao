"""Tracking service - parse carrier from tracking code and provide lookup URLs."""
import re
from ..config import GHN_TOKEN, VTP_TOKEN
from .sheets import detect_carrier

# Public tracking URLs (no token needed for manual lookup)
TRACKING_URLS = {
    "GHN": "https://tracking.ghn.vn/?order_code={code}",
    "ViettelPost": "https://viettelpost.vn/tra-cuu-van-don?order_code={code}",
    "GHTK": "https://i.giaohangtietkiem.vn/portal/tracking?code={code}",
    "J&T": "https://www.jtexpress.vn/Tracking?billcode={code}",
}

def get_tracking_url(carrier: str, code: str) -> str:
    url = TRACKING_URLS.get(carrier, "")
    return url.format(code=code) if url else ""

def parse_tracking_info(tracking_vn: str) -> dict:
    """Parse tracking VN string into carrier info with URL."""
    carrier, code = detect_carrier(tracking_vn)
    return {
        "carrier": carrier,
        "code": code,
        "url": get_tracking_url(carrier, code),
        "has_api": carrier in ("GHN", "ViettelPost") and bool(GHN_TOKEN or VTP_TOKEN),
    }
