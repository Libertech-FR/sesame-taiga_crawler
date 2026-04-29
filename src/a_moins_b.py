import os
import uuid
import requests
import logging
import urllib3

urllib3.disable_warnings()
logging.basicConfig(level=logging.INFO)
logger: logging.Logger = logging.getLogger(__name__)


async def a_moins_b(url, a, b, headers):
    force_host = os.getenv("STC_FORCE_HOST_HEADER", "0")
    forced_host = os.getenv("STC_FORCE_HOST_HEADER_VALUE") or os.getenv("STC_API_HOST")
    if forced_host and force_host.lower() in ("1", "true", "yes", "on"):
        headers = {**headers, "Host": forced_host}

    payload = {
        "jsonrpc": "2.0",
        "method": "AmoinsB",
        "params": {
            "a": a,
            "b": b,
        },
        "id": str(uuid.uuid4()),
    }
    try:
        response = requests.post(url, json=payload, headers=headers, verify=False, timeout=10000)
        response.raise_for_status()
        if response.json()['result'] != 1:
            raise Exception("Bad AmoinsB result", response.json())
        logger.info(f"API Taiga verification <{payload['id']}> successful !")
    except requests.exceptions.HTTPError as e:
        logger.warning(f"Failed to test API Taiga: {e} \n {e.response.text}")
        exit(255)
