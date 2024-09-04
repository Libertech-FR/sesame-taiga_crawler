import uuid
import requests
import logging
import urllib3
from logging import Logger

urllib3.disable_warnings()
logging.basicConfig(level=logging.INFO)
logger: Logger = logging.getLogger(__name__)


async def a_moins_b(url, a, b, headers):
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
