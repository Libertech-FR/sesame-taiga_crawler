import json
import os
import uuid
import requests
import logging
import urllib3

urllib3.disable_warnings()
logging.basicConfig(level=logging.INFO)
logger: logging.Logger = logging.getLogger(__name__)


async def export_ind(url, col, headers):
    # Optionnel : forcer l'en-tête Host (utile avec un rebond/forward et certains WAF).
    # Active via STC_FORCE_HOST_HEADER=1 et valeur via STC_FORCE_HOST_HEADER_VALUE
    # (sinon on prend STC_API_HOST).
    force_host = os.getenv("STC_FORCE_HOST_HEADER", "0")
    forced_host = os.getenv("STC_FORCE_HOST_HEADER_VALUE") or os.getenv("STC_API_HOST")
    if forced_host and force_host.lower() in ("1", "true", "yes", "on"):
        headers = {**headers, "Host": forced_host}

    payload = {
        "jsonrpc": "2.0",
        "method": col.get('method'),
        "params": col.get("params"),
        "id": str(uuid.uuid4()),
    }

    if col.get('params').get('type') == 'pri':
        #payload['params']['au'] = int(col.get('params').get('au')) + 1
        print("Type primo détecté, ajout de +1 à l'année: <" + str(payload['params']['au']) + ">")
    else:
        print("Type " + col.get('params').get('type') + " détecté, pas d'ajout à l'année: <" + str(col.get('params').get('au')) + ">")

    try:
        response = requests.post(url, json=payload, headers=headers, verify=False, timeout=10000)
        response.raise_for_status()
        if response.text == 'ko!':
            raise Exception("ko!")
        response_json = response.json()
        output = response_json.get('result', {}).get('output')
        if not output:
            logger.warning(
                "Empty response from ExportInd (type=%s, au=%s). Skipping.",
                payload['params'].get('type'),
                payload['params'].get('au'),
            )
            return
        data = output
        os.makedirs(f'./cache', exist_ok=True)
        with open(f'./cache/taiga_{col.get("params")["type"]}.json', 'w', encoding='utf-8') as fichier:
            json.dump(
                {
                    "type": data[0][0][0],
                    "data": data[0][1],
                    "total": data[0][0][1],
                },
                fichier,
                ensure_ascii=False,
                indent=4,
            )
        logger.info(f"{col.get('method')}")
    except requests.exceptions.HTTPError as e:
        logger.warning(f"Failed to insert {col.get('method')}: {e} \n {e.response.text}")
