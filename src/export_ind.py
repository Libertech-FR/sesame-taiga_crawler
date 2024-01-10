import json
import uuid
import requests
import logging
import urllib3
from logging import Logger

urllib3.disable_warnings()
logging.basicConfig(level=logging.INFO)
logger: Logger = logging.getLogger(__name__)


async def export_ind(url, col, headers):
    payload = {
        "jsonrpc": "2.0",
        "method": col.get('method'),
        "params": col.get("params"),
        "id": str(uuid.uuid4()),
    }
    try:
        response = requests.post(url, json=payload, headers=headers, verify=False, timeout=10000)
        response.raise_for_status()
        if response.text == 'ko!':
            raise Exception("ko!")
        elif not response.json()['result']['output']:
            raise Exception("Empty response from ExportInd", response.json())
        data = response.json()['result']['output']
        with open(f'./cache/taiga_{col.get("params")["type"]}.json', 'w', encoding='utf-8') as fichier:
            json.dump(
                {
                    "type": data[0][0][0],
                    "data": data[0][1],
                    "total": data[0][0][1],
                },
                fichier,
                ensure_ascii=False,
            )
        logger.info(f"{col.get('method')}")
    except requests.exceptions.HTTPError as e:
        logger.warning(f"Failed to insert {col.get('method')}: {e} \n {e.response.text}")
