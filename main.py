import asyncio
import base64
import logging
import os
from dotenv import load_dotenv
import hashlib
import sys
from datetime import datetime
import argparse

from src.a_moins_b import a_moins_b
from src.export_pictures import export_pictures
from src.export_ind import export_ind
from src.import_ind import import_ind
from src.import_pictures import import_pictures

logging.basicConfig(level=logging.INFO)
logger: logging.Logger = logging.getLogger(__name__)
load_dotenv()

basic_auth = [
    os.getenv('STC_API_USERNAME', ''),
    os.getenv('STC_API_PASSWORD', ''),
]
basic_auth = [value for value in basic_auth if value is not None]
joined_auth = ':'.join(map(str, basic_auth)).encode('utf-8')


url = f"{os.getenv('STC_API_BASEURL', 'https://taiga.archi.fr')}/taiga_libext/JsonRPC/api.php"
headers = {
    "Authorization": f"Basic {base64.b64encode(joined_auth).decode('utf-8')}",
    "Content-Type": "application/json; charset=utf-8",
}

ensa_pass = os.getenv('STC_API_PASSENSA') + datetime.now().strftime('%Y%m%d')
ensa_infos = {
    "code_ensa": os.getenv('STC_API_CODEENSA', 'lyon'),
    "pass_ensa": hashlib.sha1(ensa_pass.encode()).hexdigest(),
}

# print(ensa_infos)
# print(headers)

collections = [
    {
        "function": export_ind,
        "method": "ExportInd",
        "params": {
            **ensa_infos,
            "type": "etd",
            "id": "*",
        },
    },
    {
        "function": export_ind,
        "method": "ExportInd",
        "params": {
            **ensa_infos,
            "type": "adm",
            "id": "*",
        },
    },
    {
        "function": export_ind,
        "method": "ExportInd",
        "params": {
            **ensa_infos,
            "type": "esn",
            "id": "*",
        },
    },
    {
        "function": export_pictures,
        "method": "ExportPhotos",
        "methodBase64": "ExportPhoto",
        "params": {
            **ensa_infos,
            "type": "etd",
            "id": "*",
        },
        "paramsBase64": {
            "type": "etd",
            **ensa_infos,
        },
    },
]


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', help='all | taiga | sesame',default='all')
    parser.add_argument('--an', help='Année universitaire à importer ',default="0")
    args = parser.parse_args()
    if args.an != 0 :
        print(f"Import pour l'annee {args.an}")
        for col in collections:
            col.get('params')['au']=int(args.an)

    if args.run == 'taiga' or args.run == 'all':
        logger.info("Starting Taiga crawler...")
        await a_moins_b(url, 0, -1, headers)
        collection_tasks = [col.get('function')(url, col, headers) for col in collections]
        await asyncio.gather(*collection_tasks)
        print("Taiga crawler ended successful !!!")
    if args.run == 'sesame' or args.run == 'all':
        print("Starting import_ind...")
        start_time = datetime.now()
        await import_ind()
        await import_pictures()
        end_time = datetime.now()
        execution_time = end_time - start_time
        print(f"import_ind completed in {execution_time}")

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    finally:
        loop.close()
