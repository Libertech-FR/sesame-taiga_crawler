import asyncio
import json
import os
from data_weaver import weave_entries, weave_entry
import aiohttp
import dotenv

dotenv.load_dotenv()
sesame_api_baseurl = os.getenv('SESAME_API_BASEURL')

configs = {
    "taiga_etd.json": {
        "mapping": {
            "nom": "inetOrgPerson.cn",
            "prenom": ["inetOrgPerson.sn", "inetOrgPerson.givenName", "additionalFields.attributes.supann.supannPrenomsEtatCivil"],
            "id_coord": ["inetOrgPerson.uid", "additionalFields.attributes.supann.supannRefId"],
            "email1": "inetOrgPerson.mail",
            "tel_mob": "inetOrgPerson.mobile",
            "adresse": "inetOrgPerson.postalAddress",
            "mot_de_passe_ldap": "inetOrgPerson.userPassword",
            "civilite": ["additionalFields.attributes.supann.supanncivilite", "additionalFields.attributes.supann.supannOIDCGenre"],
            "nom_marital": "additionalFields.attributes.supann.supannNomdeNaissance",
            "nss_date": "additionalFields.attributes.supann.supannOIDCDatedeNaissance",
            "nns_pays": "additionalFields.attributes.supann.supannCodeINSEEPaysDeNaissance",
            "nss_ville": "additionalFields.attributes.supann.supannCodeINSEEVilleDeNaissance",
            "email2": "additionalFields.attributes.supann.supannAutreMail",
            #"sesame": "additionalFields.attributes.supann.supannListeRouge",
            #"outil de messagerie ou sesame ?": "additionalFields.attributes.mailForwardingAddress",
            #"taiga + sesame": "additionalFields.attributes.supann.supannMailPerso",
            #"calculé": "additionalFields.attributes.supann.supannRessourceEtatDate",
            #"saisie": "additionalFields.attributes.supann.supannEntiteAffectationPrincipale"
        },
        "additionalFields": {
            "additionalFields.objectClasses": ["supann"],
            "additionalFields.attributes.supann.supannTypeEntiteAffectation": "etd",
            "state": -1,
        }
    },
    "taiga_adm.json": {
        "mapping": {
            "nom": "inetOrgPerson.cn",
            "prenom": ["inetOrgPerson.sn", "inetOrgPerson.givenName", "additionalFields.attributes.supann.supannPrenomsEtatCivil"],
            "id_coord": ["inetOrgPerson.uid", "additionalFields.attributes.supann.supannEmpId"],
            "email1": "inetOrgPerson.mail",
            "tel_mob": "inetOrgPerson.mobile",
            "adresse": "inetOrgPerson.postalAddress",
            "mot_de_passe_ldap": "inetOrgPerson.userPassword",
            "civilite": ["additionalFields.attributes.supann.supanncivilite", "additionalFields.attributes.supann.supannOIDCGenre"],
            "nom_marital": "additionalFields.attributes.supann.supannNomdeNaissance",
            "nss_date": "additionalFields.attributes.supann.supannOIDCDatedeNaissance",
            "nns_pays": "additionalFields.attributes.supann.supannCodeINSEEPaysDeNaissance",
            "nss_ville": "additionalFields.attributes.supann.supannCodeINSEEVilleDeNaissance",
            "email2": "additionalFields.attributes.supann.supannAutreMail",
            #"sesame": "additionalFields.attributes.supann.supannListeRouge",
            #"outil de messagerie ou sesame ?": "additionalFields.attributes.mailForwardingAddress",
            #"taiga + sesame": "additionalFields.attributes.supann.supannMailPerso",
            #"calculé": "additionalFields.attributes.supann.supannRoleGenerique",
            #"saisie": "additionalFields.attributes.supann.supannParrainDN",
            #"calcué": "additionalFields.attributes.supann.supannTypeEntiteAffectation",
            #"": "additionalFields.attributes.supann.supannActivite",
            #"taiga, sesame ou fixe": "additionalFields.attributes.supann.supannEmpDateFin"
        },
        "additionalFields": {
            "additionalFields.objectClasses": ["supann"],
            "additionalFields.attributes.supann.supannTypeEntiteAffectation": "adm",
            "state": -1,
        }
    },
    "taiga_esn.json": {
        "mapping": {
            "nom": "inetOrgPerson.cn",
            "prenom": ["inetOrgPerson.sn", "inetOrgPerson.givenName", "additionalFields.attributes.supann.supannPrenomsEtatCivil"],
            "id_coord": ["inetOrgPerson.uid", "additionalFields.attributes.supann.supannEmpId"],
            "email1": "inetOrgPerson.mail",
            "tel_mob": "inetOrgPerson.mobile",
            "adresse": "inetOrgPerson.postalAddress",
            "mot_de_passe_ldap": "inetOrgPerson.userPassword",
            "civilite": ["additionalFields.attributes.supann.supanncivilite", "additionalFields.attributes.supann.supannOIDCGenre"],
            "nom_marital": "additionalFields.attributes.supann.supannNomdeNaissance",
            "nss_date": "additionalFields.attributes.supann.supannOIDCDatedeNaissance",
            "nns_pays": "additionalFields.attributes.supann.supannCodeINSEEPaysDeNaissance",
            "nss_ville": "additionalFields.attributes.supann.supannCodeINSEEVilleDeNaissance",
            "email2": "additionalFields.attributes.supann.supannAutreMail",
            #"sesame": "additionalFields.attributes.supann.supannListeRouge",
            #"outil de messagerie ou sesame ?": "additionalFields.attributes.mailForwardingAddress",
            #"taiga + sesame": "additionalFields.attributes.supann.supannMailPerso",
            #"calculé": "additionalFields.attributes.supann.supannRoleGenerique",
            #"saisie": "additionalFields.attributes.supann.supannParrainDN",
            #"calcué": "additionalFields.attributes.supann.supannTypeEntiteAffectation",
            #"": "additionalFields.attributes.supann.supannActivite",
            #"taiga, sesame ou fixe": "additionalFields.attributes.supann.supannEmpDateFin"
        },
        "additionalFields": {
            "additionalFields.objectClasses": ["supann"],
            "additionalFields.attributes.supann.supannTypeEntiteAffectation": "esn",
            "state": -1,
        }
    },
}

async def gather_with_concurrency(n, tasks):
    semaphore = asyncio.Semaphore(n)

    async def sem_task(task):
        async with semaphore:
            await asyncio.sleep(0.1)  # Simulate i/o time
            return await task

    return await asyncio.gather(*[sem_task(task) for task in tasks])

async def send_request(session, url, json):
    token = os.getenv('SESAME_API_TOKEN')
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }

    try:
        print(f"json: {json}")
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

async def import_ind():
    cache_files = os.listdir('./cache')
    datas = {}
    for file in cache_files:
        with open(f'./cache/{file}', 'r', encoding='utf-8') as fichier:
            datas[file] = json.load(fichier).get('data')

    async with aiohttp.ClientSession() as session:
        # for file in cache_files:
        #     await process_data(datas[file], configs[file], file, session)
        tasks = [process_data(datas[file], configs[file], file, session) for file in cache_files]
        await gather_with_concurrency(10, tasks)
