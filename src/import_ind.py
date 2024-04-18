import asyncio
import json
import os
from data_weaver import weave_entries, weave_entry
import aiohttp
import dotenv
import yaml

dotenv.load_dotenv()
sesame_api_baseurl = os.getenv('SESAME_API_BASEURL')
sesame_api_token = os.getenv('SESAME_API_TOKEN')

async def gather_with_concurrency(n, tasks):
    semaphore = asyncio.Semaphore(n)

    async def sem_task(task):
        async with semaphore:
            await asyncio.sleep(0.1)  # Simulate i/o time
            return await task

    return await asyncio.gather(*[sem_task(task) for task in tasks])

async def send_request(session, url, json):
    headers = {
        "Authorization": f"Bearer {sesame_api_token}",
        "Content-Type": "application/json; charset=utf-8",
    }

    try:
        async with session.post(url, json=json, headers=headers) as response:
            response.raise_for_status()  # Raises error for 4xx/5xx responses
            print(f"Request to {url} successful: {response.status}")
    except aiohttp.ClientError as e:
        print(f"Request to {url} failed: {e}")
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
        json.dump(result, fichier, ensure_ascii=False)
    tasks = [send_request(session, f'{sesame_api_baseurl}/management/identities/upsert', entry) for entry in result]
    await gather_with_concurrency(25, tasks)
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
        await gather_with_concurrency(10, tasks)
