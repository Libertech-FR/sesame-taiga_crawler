import asyncio
import json
import logging
import os
from lib.data_weaver3 import weave_entry
import aiohttp
import dotenv
import yaml
import re

logger = logging.getLogger(__name__)

dotenv.load_dotenv()
sesame_api_baseurl = os.getenv('SESAME_API_BASEURL')
sesame_api_token = os.getenv('SESAME_API_TOKEN')
sesame_import_parallels_files = int(os.getenv('SESAME_IMPORT_PARALLELS_FILES', 1))
sesame_import_parallels_entries = int(os.getenv('SESAME_IMPORT_PARALLELS_ENTRIES', 1))

async def gather_with_concurrency(n, tasks):
    semaphore = asyncio.Semaphore(n)

    async def sem_task(task):
        async with semaphore:
            await asyncio.sleep(0.1)  # Simulate i/o time
            return await task

    return await asyncio.gather(*[sem_task(task) for task in tasks])

async def read_response(response):
    message = await response.content.read()
    jsonMessage = json.loads(message)
    print(jsonMessage)

async def send_request(session, url,exclusions, json, force):
    if (json.get('inetOrgPerson', {}).get('employeeNumber') is None and json.get('$setOnInsert', {}).get('inetOrgPerson', {}).get('employeeNumber') is None):
        print(f"MISSING employeeNumber -> $set: {json.get('inetOrgPerson', {})}, $setOnInsert: {json.get('$setOnInsert', {}).get('inetOrgPerson', {})}")
        return

    headers = {
        "Authorization": f"Bearer {sesame_api_token}",
        "Content-Type": "application/json; charset=utf-8",
    }
    params = {
    #     "filters[inetOrgPerson.employeeNumber]": f"{json.get('inetOrgPerson', {}).get('employeeNumber')}",
        "filters[inetOrgPerson.employeeType]": "TAIGA",
        "force": force,
    }

    employeeNumber = json.get('inetOrgPerson', {}).get('employeeNumber') or json.get('$setOnInsert', {}).get('inetOrgPerson', {}).get('employeeNumber')

    if isinstance(employeeNumber, list):
        params["filters[inetOrgPerson.employeeNumber][]"] = employeeNumber
    else:
        params["filters[inetOrgPerson.employeeNumber]"] = employeeNumber

    for regex in exclusions:
        for r in regex:
            # Handle nested attributes with dot notation (parent.enfant ...)
            if '.' in r:
                parts = r.split('.')
                current = json
                for part in parts:
                    if current and isinstance(current, dict) and part in current:
                        current = current.get(part)
                    else:
                        current = None
                        break
                value = current
            else:
                # Default to inetOrgPerson if no dot in attribute name
                value = json.get('inetOrgPerson', {}).get(r)

            if value:
                result = re.search(regex[r], value)
                if result is not None:
                    print(f"EXCLUDED {json.get('inetOrgPerson', {}).get('employeeNumber')} {json.get('inetOrgPerson', {}).get('cn')}")
                    return
    try:
        print(f"Sending request to {url} with query: {params}")

        async with session.post(url, json=json, headers=headers, params=params) as response:
            #print(f"Request to {url} successful: {response.status}")
            if response.status == 304:
                print(f"{response.status} UNMODIFIED {json.get('inetOrgPerson', {}).get('employeeNumber')} {json.get('inetOrgPerson', {}).get('cn')}")
            elif response.status == 200:
                print(f"{response.status} MODIFIED {json.get('inetOrgPerson', {}).get('employeeNumber')} {json.get('inetOrgPerson', {}).get('cn')}")
            elif response.status == 201:
                print(f"{response.status} ADDED {json.get('inetOrgPerson', {}).get('employeeNumber')} {json.get('inetOrgPerson', {}).get('cn')}")
            elif response.status == 202:
                print(f"{response.status} ADDED WiTH WARNiNG {json.get('inetOrgPerson', {}).get('employeeNumber')} {json.get('inetOrgPerson', {}).get('cn')}")
            else:
                print(f"{response.status} -- {json.get('inetOrgPerson', {}).get('employeeNumber')} {json.get('inetOrgPerson', {}).get('cn')}")
                await read_response(response)
            response.raise_for_status()  # Raises error for 4xx/5xx responses
    except aiohttp.ClientResponseError as e:
        # This catches responses like 400, 404, 500 etc.
        print(f"Request to {url} failed with status {e.status}: {e.message}")
    except aiohttp.ClientError as e:
        print(f"Request to {url} failed: {str(e)}")
    except asyncio.TimeoutError:
        print(f"Request to {url} timed out")

async def get_data(data, config):
    result = []
    for entry in data:
        treated = weave_entry(entry, config)
        result.append(treated)
    return result



async def process_data(data, config, file, session, force):
    print(f"Processing {file}")
    result = await get_data(data, config)
    with open(f'./data/{file}', 'w', encoding='utf-8') as fichier:
        json.dump(result, fichier, ensure_ascii=False, indent=4)
    tasks = [send_request(session, f'{sesame_api_baseurl}/management/identities/upsert',config.get('exclude',[]),entry, force) for entry in result]
    await gather_with_concurrency(sesame_import_parallels_files, tasks)
    print(f"Processed {file}")

async def load_config():
    config_file=os.getenv('CONFIG_FILE_TRANSFORM','./config.yml')
    with open(config_file, 'r', encoding='utf-8') as fichier:
        docs = [doc for doc in yaml.safe_load_all(fichier) if doc is not None]

    if not docs:
        return {}

    if len(docs) == 1:
        if not isinstance(docs[0], dict):
            raise ValueError(f"Invalid config format in {config_file}: expected mapping")
        return docs[0]

    merged: dict = {}
    for idx, doc in enumerate(docs, start=1):
        if not isinstance(doc, dict):
            raise ValueError(f"Invalid config format in {config_file} (document #{idx}): expected mapping")
        merged.update(doc)
    return merged

def _load_cache_datas(cache_dir: str, configs: dict) -> dict:
    """Load and return the 'data' payload of each cache file listed in configs.

    Files that don't exist, are empty, or contain invalid JSON are logged as
    warnings and skipped so one corrupted cache file doesn't abort the whole
    import run. Files in cache_dir that aren't mentioned in configs are ignored
    silently.

    Args:
        cache_dir: Path to the directory containing cache JSON files.
        configs: Mapping from cache filename to its transformation config.

    Returns:
        dict: {filename: data_list} for each successfully loaded file.
    """
    datas: dict = {}
    try:
        cache_files = os.listdir(cache_dir)
    except FileNotFoundError:
        logger.warning("Cache directory %s does not exist", cache_dir)
        return datas

    for file in cache_files:
        if file not in configs:
            continue
        path = os.path.join(cache_dir, file)
        try:
            with open(path, 'r', encoding='utf-8') as fh:
                payload = json.load(fh)
        except json.JSONDecodeError as e:
            logger.warning("Skipping %s: invalid JSON (%s)", path, e)
            continue
        except OSError as e:
            logger.warning("Skipping %s: read error (%s)", path, e)
            continue
        if not isinstance(payload, dict):
            logger.warning("Skipping %s: expected dict payload, got %s", path, type(payload).__name__)
            continue
        data = payload.get('data')
        if not data:
            logger.warning("Skipping %s: missing or empty 'data' key", path)
            continue
        datas[file] = data
        print(f"Loaded {file}")
    return datas


async def import_ind(force: bool):
    configs = await load_config()
    datas = _load_cache_datas('./cache', configs)

    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [process_data(datas[file], configs[file], file, session, force) for file in datas]
        await gather_with_concurrency(sesame_import_parallels_files, tasks)
