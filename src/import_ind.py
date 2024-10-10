import asyncio
import json
import os
from lib.data_weaver3 import weave_entry
import aiohttp
import dotenv
import yaml
import re

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

async def send_request(session, url,exclusions, json):
    headers = {
        "Authorization": f"Bearer {sesame_api_token}",
        "Content-Type": "application/json; charset=utf-8",
    }
    params = {
        "filters[inetOrgPerson.employeeNumber]": f"{json.get('inetOrgPerson', {}).get('employeeNumber')}",
        "filters[inetOrgPerson.employeeType]": "TAIGA",
    }
    for regex in exclusions:
        for r in regex:
            value=json.get('inetOrgPerson').get(r)
            if value:
                result=re.search(regex[r],value)
                if result != None:
                    print(f"EXCLUDED {json.get('inetOrgPerson', {}).get('employeeNumber')} {json.get('inetOrgPerson', {}).get('cn')}")
                    return
    try:

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
        treated = await weave_entry(entry, config)
        result.append(treated)
    return result



async def process_data(data, config, file, session):
    print(f"Processing {file}")
    result = await get_data(data, config)
    with open(f'./data/{file}', 'w', encoding='utf-8') as fichier:
        json.dump(result, fichier, ensure_ascii=False, indent=4)
    exclude=config.get('exclude',[])
    tasks = [send_request(session, f'{sesame_api_baseurl}/management/identities/upsert',config.get('exclude',[]),entry) for entry in result]
    await gather_with_concurrency(sesame_import_parallels_files, tasks)
    print(f"Processed {file}")

async def load_config():
    with open('./config.yml', 'r', encoding='utf-8') as fichier:
        return yaml.load(fichier, Loader=yaml.FullLoader)

async def import_ind():
    configs = await load_config()
    cache_files = os.listdir('./cache')
    datas = {}
    for file in cache_files:
        if file in configs.keys():
          print(f"Loading {file}, keys: {configs.keys()}")
          with open(f'./cache/{file}', 'r', encoding='utf-8') as fichier:
              datas[file] = json.load(fichier).get('data')

    async with aiohttp.ClientSession() as session:
        tasks = [process_data(datas[file], configs[file], file, session) for file in cache_files if file in configs.keys()]
        await gather_with_concurrency(sesame_import_parallels_files, tasks)
