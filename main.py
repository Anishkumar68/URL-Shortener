from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl
from typing import Dict
from user_agents import parse
import string
from time import time
import requests
from datetime import datetime, timezone


app = FastAPI()


# Rate limit settings
rate_limit_window = 60  # seconds
rate_limit_max_requests = 5

# IP -> list of timestamps
rate_limit_cache: Dict[str, list] = {}


# In-memory databases
url_db: Dict[str, str] = {}
reverse_db: Dict[str, str] = {}
visitor_logs: Dict[str, list] = {}
counter = 1

BASE62 = string.digits + string.ascii_letters


def encode_base62(num: int) -> str:
    result = []
    while num > 0:
        num, rem = divmod(num, 62)
        result.append(BASE62[rem])
    return "".join(reversed(result)) or "0"


class URLRequest(BaseModel):
    url: HttpUrl


def check_rate_limit(ip: str):
    now = time()
    window_start = now - rate_limit_window

    # Get timestamps for this IP
    timestamps = rate_limit_cache.get(ip, [])

    # Remove old timestamps outside the window
    recent_requests = [ts for ts in timestamps if ts > window_start]

    if len(recent_requests) >= rate_limit_max_requests:
        raise HTTPException(
            status_code=429, detail="Rate limit exceeded. Try again later."
        )

    # Save updated request list
    recent_requests.append(now)
    rate_limit_cache[ip] = recent_requests


@app.post("/shorten")
async def shorten_url(request: URLRequest, req: Request):
    """
    takes input a long url, returns a short url
    """
    client_ip = req.client.host
    check_rate_limit(client_ip)
    global counter
    long_url = request.url

    if long_url in reverse_db:
        short_code = reverse_db[str(long_url)]
    else:
        short_code = encode_base62(counter)
        url_db[short_code] = str(long_url)
        reverse_db[str(long_url)] = short_code
        counter += 1

    short_url = f"http://localhost:8000/{short_code}"
    return {"short_url": short_url}


def get_visitor_info(request: Request) -> dict:
    """
    returns visitor info
    """
    ip = request.client.host
    user_agent = request.headers.get("user-agent", "")
    parsed_ua = parse(user_agent)
    device = (
        "Mobile" if parsed_ua.is_mobile else "Tablet" if parsed_ua.is_tablet else "PC"
    )
    browser = f"{parsed_ua.browser.family} {parsed_ua.browser.version_string}"

    try:
        location_data = requests.get(f"http://ip-api.com/json/{ip}").json()
        city = location_data.get("city") or "Unknown"
        country = location_data.get("country") or "Unknown"
        location = f"{city}, {country}"
    except:
        location = "Unknown"

    return {
        "ip": ip,
        "device": device,
        "browser": browser,
        "location": location,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/{short_code}")
async def redirect(short_code: str, request: Request):
    """
    redirects to original url
    and logs visitor info
    """
    check_rate_limit(request.client.host)
    if short_code not in url_db:
        raise HTTPException(status_code=404, detail="Short URL not found")

    original_url = url_db[short_code]

    info = get_visitor_info(request)
    if short_code not in visitor_logs:
        visitor_logs[short_code] = []
    visitor_logs[short_code].append(info)

    return RedirectResponse(url=original_url)


@app.get("/stats/{short_code}")
async def get_stats(short_code: str):
    """
    returns stats
    """

    if short_code not in url_db:
        raise HTTPException(status_code=404, detail="Short URL not found")

    logs = visitor_logs.get(short_code, [])
    return {
        "short_code": short_code,
        "original_url": url_db[short_code],
        "visit_count": len(logs),
        "visitors": logs,
    }
