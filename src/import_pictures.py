import asyncio
import json
import os
import aiohttp
import dotenv

dotenv.load_dotenv()
sesame_api_baseurl = os.getenv('SESAME_API_BASEURL')
sesame_api_token = os.getenv('SESAME_API_TOKEN')
sesame_import_parallels_files = int(os.getenv('SESAME_IMPORT_PARALLELS_FILES', 1))
sesame_import_parallels_entries = int(os.getenv('SESAME_IMPORT_PARALLELS_ENTRIES', 5))

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

async def send_request(session, url, json):
    print(f"Sending request to {url} with {json.get('id')}")
    headers = {
        "Authorization": f"Bearer {sesame_api_token}",
    }
    params = {
        "filters[customFields.photo]": f"{json.get('id')}.jpg",
        "filters[inetOrgPerson.employeeType]": "TAIGA",
    }

    # print('filters', params)

    try:
        form = aiohttp.FormData()
        form.add_field('file', json.get('file'), filename='photoJpeg.jpg', content_type='image/jpeg')

        async with session.post(url, data=form, headers=headers, params=params) as response:
            print(f"Request to {url} successful: {response.status}")
            if response.status == 304:
                print(f"Cached entry {json.get('id')}")
            else:
                print(f"Response to {json.get('id')}:")
                await read_response(response)
            response.raise_for_status()  # Raises error for 4xx/5xx responses
    except aiohttp.ClientResponseError as e:
        # This catches responses like 400, 404, 500 etc.
        print(f"Request to {url} failed with status {e.status}: {e.message}")
    except aiohttp.ClientError as e:
        print(f"Request to {url} failed: {str(e)}")
    except asyncio.TimeoutError:
        print(f"Request to {url} timed out")

async def process_data(data, file, session):
    files = []
    print(f"Processing pictures {file}")

    for entry in data:
        with open(f'./cache/pictures/files/{entry["ident"]}.jpg', 'rb') as fichier:
            print(f"Reading picture {entry['ident']}.jpg")
            picture = fichier.read()
            files.append({
                "id": entry["ident"],
                "file": picture,
            })

    tasks = [send_request(session, f'{sesame_api_baseurl}/management/identities/upsert/photo', part) for part in files]
    await gather_with_concurrency(sesame_import_parallels_files, tasks)
    print(f"Processed pictures {file}")

def list_files_in_dir(directory):
    files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    return files

def filter_datas(datasCurrent, datasOld):
    datas = []
    old_data_tuples = {(data['ident'], data['size'], data['date']) for data in datasOld}

    for data in datasCurrent:
        data_tuple = (data['ident'], data['size'], data['date'])
        if data_tuple not in old_data_tuples:
            datas.append(data)

    return datas

async def import_pictures():
    cache_files = os.listdir('./cache/pictures/files')
    datasCurrent = {}
    datasOld = {}
    datas = {}

    files = list_files_in_dir('./cache/pictures')

    # for file in files:
    #     if file.endswith(".old"):
    #         with open(f'./cache/pictures/{file}', 'r', encoding='utf-8') as fichier:
    #             datasOld[file.split('.')[0]] = json.load(fichier).get('data')
    #     else:
    with open(f'./cache/pictures/{file}', 'r', encoding='utf-8') as fichier:
        datasCurrent[file.split('.')[0]] = json.load(fichier).get('data')

    # for file in files:
    #     if datasOld.get(file.split('.')[0]) is not None:
    #         datas[file.split('.')[0]] = filter_datas(datasCurrent[file.split('.')[0]], datasOld[file.split('.')[0]])
    #     else:
    datas[file.split('.')[0]] = datasCurrent[file.split('.')[0]]

    # print(datasOld)
    # print(datasCurrent)
    # print(datas)

    async with aiohttp.ClientSession() as session:
        tasks = [process_data(datas[entry], entry, session) for entry in datas]
        await gather_with_concurrency(sesame_import_parallels_files, tasks)
