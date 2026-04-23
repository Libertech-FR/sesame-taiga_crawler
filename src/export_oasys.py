import json
import os
import requests
import logging
import urllib3

urllib3.disable_warnings()
logging.basicConfig(level=logging.INFO)
logger: logging.Logger = logging.getLogger(__name__)


async def export_oasys(url, col, headers):
    my_url = ''
    if col.get('params').get('type') == 'etd':
        my_url = url + '/' + col.get('params').get('method') + '?year=' + col.get('params').get('au') + '&offset=0&limit=10000'
    try:
        response = requests.get(my_url, headers=headers, verify=False, timeout=10000)
        response.raise_for_status()
        if response.text == 'ko!':
            raise Exception("ko!")
        elif not response.json()['data']:
            raise Exception("Empty response from ExportInd", response.json())
        data = response.json()
        os.makedirs('./cache', exist_ok=True)
        with open(f'./cache/oasys_{col.get("params")["type"]}.json', 'w', encoding='utf-8') as fichier:
            json.dump(
                {
                    "type": col.get("params")["type"],
                    "data": data['data'],
                    "total": data['meta']['pagination']['count'],
                },
                fichier,
                ensure_ascii=False,
                indent=4,
            )
        logger.info(f"{col.get('method')}")
    except requests.exceptions.HTTPError as e:
        response_text = e.response.text if getattr(e, "response", None) is not None else "No response body"
        logger.warning(f"Failed to insert {col.get('method')}: {e} \n {response_text}")
