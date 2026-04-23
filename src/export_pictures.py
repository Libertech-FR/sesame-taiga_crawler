import json
import os
import uuid
import requests
import base64
import logging
import urllib3

urllib3.disable_warnings()
logging.basicConfig(level=logging.INFO)
logger: logging.Logger = logging.getLogger(__name__)

async def export_pictures(url, col, headers):
    params = {k: v for k, v in col.get("params", {}).items() if k != "au"}
    payload = {
        "jsonrpc": "2.0",
        "method": col.get('method'),
        "params": params,
        "id": str(uuid.uuid4()),
    }
    try:
        response = requests.post(url, json=payload, headers=headers, verify=False, timeout=10000)
        response.raise_for_status()
        print(payload)
        print(response.json())
        if response.text == 'ko!':
            raise Exception("ko!")
        elif not response.json()['result']['output']:
            raise Exception("Empty response from ExportPhotos", response.json())
        data = response.json()['result']['output']
        os.makedirs(f'./cache', exist_ok=True)
        os.makedirs(f'./cache/pictures', exist_ok=True)

        if os.path.exists(f'./cache/pictures/taiga_{col.get("params")["type"]}.json'):
            logger.info(f'<./cache/pictures/taiga_{col.get("params")["type"]}.json> Already exists checking datas...')

        with open(f'./cache/pictures/taiga_{col.get("params")["type"]}.json', 'w', encoding='utf-8') as fichier:
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
        logger.info(f'<./cache/pictures/taiga_{col.get("params")["type"]}.json> No old file found, starting exportation...')
        for picture in data[0][1]:
            await export_picture(url, col, headers, picture.get('ident'))
    except requests.exceptions.HTTPError as e:
        logger.warning(f"Failed to insert {col.get('method')}: {e} \n {e.response.text}")


async def export_picture(url, col, headers, id):
    payload = {
        "jsonrpc": "2.0",
        "method": col.get('methodBase64'),
        "params": {
            **col.get("paramsBase64"),
            "id": id.replace(col.get("paramsBase64").get('type') + '-', ''),
        },
        "id": str(uuid.uuid4()),
    }

    try:
        response = requests.post(url, json=payload, headers=headers, verify=False, timeout=10000)
        response.raise_for_status()
        if response.text == 'ko!':
            raise Exception("ko!")
        elif not response.json()['result']['output']:
            raise Exception("Empty response from ExportPhoto", response.json())
        data = response.json()['result']['output']
        os.makedirs(f'./cache/pictures/files', exist_ok=True)
        with open(f'./cache/pictures/files/{id}.jpg', 'wb') as fichier:
            fichier.write(base64.b64decode(data[0][0].get('fichier')))
        logger.info(f"{col.get('methodBase64')} -> {id}")
    except requests.exceptions.HTTPError as e:
        logger.warning(f"Failed to insert {col.get('methodBase64')}: {e} \n {e.response.text}")
