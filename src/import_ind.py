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
    employee_number_key=json.get('inetOrgPerson', {}).get('employeeNumber')
    if employee_number_key is None:
        employee_number_key = json.get('$setOnInsert',{}).get('inetOrgPerson', {}).get('employeeNumber')
    params = {
        "filters[inetOrgPerson.employeeNumber]": employee_number_key,
        "filters[inetOrgPerson.employeeType]": "TAIGA",
    }
    for regex in exclusions:
        for r in regex:
            value=json.get('inetOrgPerson').get(r)
            if value:
                result=re.search(regex[r],value)
                if result != None:
                    print(f"EXCLUDED {employee_number_key[0]} {json.get('inetOrgPerson', {}).get('cn')}")
                    return
    try:

        async with session.post(url, json=json, headers=headers, params=params) as response:
            #print(f"Request to {url} successful: {response.status}")
            if response.status == 304:
                print(f"{response.status} UNMODIFIED {employee_number_key[0]} {json.get('inetOrgPerson', {}).get('cn')}")
            elif response.status == 303:
                print(f"{response.status} NOT CONCERNED FUSIONNED {employee_number_key[0]} {json.get('inetOrgPerson', {}).get('cn')}")
            elif response.status == 200:
                print(f"{response.status} MODIFIED {employee_number_key[0]} {json.get('inetOrgPerson', {}).get('cn')}")
            elif response.status == 201:
                print(f"{response.status} ADDED {employee_number_key[0]} {json.get('inetOrgPerson', {}).get('cn')}")
            elif response.status == 202:
                print(f"{response.status} ADDED WiTH WARNiNG {employee_number_key[0]} {json.get('inetOrgPerson', {}).get('cn')}")
            else:
                print(f"{response.status} -- {employee_number_key[0]} {json.get('inetOrgPerson', {}).get('cn')}")
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
    for entry in result:
        await send_request(session, f'{sesame_api_baseurl}/management/identities/upsert',config.get('exclude',[]),entry)
    print(f"Processed {file}")

async def load_config():
    orchestrator_version=await getVersion()
    print (f"Orchestrator version : {orchestrator_version}")
    with open('./config.yml', 'r', encoding='utf-8') as fichier:
        config = yaml.load(fichier, Loader=yaml.FullLoader)
        if orchestrator_version > 116:
            for f in config.keys():
                test = config.get(f).get('mapping').get('inetOrgPerson.employeeNumber')
                if test is None:
                    test = config.get(f).get('mapping').get('$setOnInsert.inetOrgPerson.employeeNumber')
                if test is None:
                    print('Erreur: impossible de trouver le champs inetOrgPerson.employeeNumber')
                    exit(1)
                if type(test) != list:
                    print(f"config.yml incompatible avec la version de l'orchestrator: {orchestrator_version}")
                    print("Le champ inetOrgPerson.employeeNumber doit être de type multi-valeur")
                    print("Exemple : ")
                    print("inetOrgPerson.employeeNumber:")
                    print("- id_coord")
                    print("A la place de : ")
                    print("inetOrgPerson.employeeNumber: id_coord")
                    exit(1)
        return config


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


async def getVersion():
    async with aiohttp.ClientSession() as session:
        async with session.get(sesame_api_baseurl) as response:
            json = await response.json()
            version_str=json['version'].split('.')
            version=int(version_str[0])*100 + int(version_str[1])*10 +int(version_str[2])
            return(version)


