import json
import asyncio
import aiofiles
from yaml import CLoader as Loader
from lib.data_weaver3.utils import crush, construct
from lib.data_weaver3.transforms import parse_transform
import csv
import yaml
import os

config = {}

def handle_value(data, source_key, target_key, default=False):
    """
    Handles the value of the given key in the data dictionary.

    Args:
        data (dict): The data dictionary.
        source_key (str | dict | list): The source key to retrieve the value from.
        target_key (str): The key to store the value in the final result.
        default (bool, optional): Whether to handle default values. Defaults to True.
    """
    def get_value_with_default(src_key):
        """
        Retrieves the value of the given key from the data dictionary.


        Args:
            src_key (str): The key to retrieve the value for.

        Returns:
            Any: The value of the key.
            Bool: Whether the value is a default value.
        """
        value = data.get(src_key)
        if not value and default:
            return handle_default_value(data, target_key), True
        return value, False

    def handle_dict(source_key: dict):
        """

        Handles the dictionary value of the given key in the data dictionary.

        Args:
            source_key (dict): The key to retrieve the value from.

        Returns:
            dict: The handled dictionary.

        """
        handled_dict, is_default = {sub_key: get_value_with_default(sub_key)[0] for sub_key in source_key}, any(get_value_with_default(sub_key)[1] for sub_key in source_key)
        if is_default:
            return handled_dict
        return transform_value(handled_dict, target_key)

    def handle_list(source_key: list):
        """
        Handles the list value of the given key in the data dictionary.

        Args:
            source_key (list): The key to retrieve the value from.

        Returns:
            list: The handled list.

        """
        handled_list, is_default = [get_value_with_default(sub_key)[0] for sub_key in source_key], all(get_value_with_default(sub_key)[1] for sub_key in source_key)
        if is_default:
            return handled_list
        return transform_value(handled_list, target_key)

    def handle_default(source_key):
        """
        Handles the default value for the given key.

        Args:
            source_key (str): The key to retrieve the value from.

        Returns:
            Any: The handled value.
        """
        handled_value, is_default = get_value_with_default(source_key)
        if is_default:
            return handled_value
        return transform_value(handled_value, target_key)

    type_handlers = {
        dict: handle_dict,
        list: handle_list,
    }

    handler = type_handlers.get(type(source_key), handle_default)
    value = handler(source_key)
    return value

def handle_default_value(data, target_key):
    """
    Handles the default value for the given key.

    Args:
        data (dict): The data dictionary.
        key (str): The key to retrieve the default value for.
    """
    default_source_key = config.get('default', {}).get('dynamic', {}).get(target_key)
    if default_source_key is not None:
        value = handle_value(data, default_source_key, target_key, False)
        return transform_value(value, target_key, True)

    default_source_value = config.get('default', {}).get('static', {}).get(target_key)
    if default_source_value is not None:
        return default_source_value

    return None


def transform_value(value, field, default=False):
    """
    Transforms the given value based on the configuration.

    Args:
        value (Any): The value to transform.
        field (str): The field name.
        default (bool, optional): Whether to use the default configuration. Defaults to False.

    Returns:
        Any: The transformed value.
    """
    if default:
        transform = config.get('default', {}).get('transforms', {}).get(field)
    else:
        transform = config.get('transforms', {}).get(field)
    if transform and value is None:
        return value
    if isinstance(transform, list):
        for t in transform:
            value = parse_transform(t, value)
        return value
    if transform:
        return parse_transform(transform, value)
    return value

async def map_fields(data: dict, final_result):
    """
    Maps the fields of the data dictionary to the final_result dictionary based on the configuration.
    Args:
        data (dict): The input data dictionary.
        final_result (dict): The dictionary to store the mapped key-value pairs.

    Returns:
        None
    """

    for key, source_key in config.get('mapping').items():
        value = handle_value(data, source_key, key)
        final_result[key] = value

    for key, value in config.get('additionalFields').items():
        final_result[key] = value

async def process_entry(entry):
    final_result = {}
    flat_object = crush(entry)
    await map_fields(flat_object, final_result)
    return construct(final_result)

async def process_entries(entries):
    """
    Process a list of entries asynchronously.

    Args:
        entries (list): A list of entries to process.

    Returns:
        list: A list of constructed objects.

    """
    final_list = []
    tasks = [process_entry(entry) for entry in entries]
    final_list = await asyncio.gather(*tasks)
    return final_list

async def load_config(configContent=None):
    """
    Loads the configuration from a JSON file.

    Returns:
        dict: The configuration dictionary.

    """
    if configContent is None:
        async with aiofiles.open('./config/config.yml', 'r', encoding='utf8') as file:
            content = await file.read()
            configContent = yaml.load(content, Loader=Loader)
    config.update(configContent)

    if config.get('mapping') is None:
        raise Exception('Invalid config file!')
    if config.get('additionalFields') is None:
        config['additionalFields'] = {}

async def save_result_to_file(result, file_path):
    # Determine the file extension
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()

    if ext not in ['.csv', '.json', '.yml', '.yaml']:
        print('Invalid file extension. Defaulting to JSON.')
        ext = '.json'

    # Asynchronously write the result to the file based on the extension
    async with aiofiles.open(file_path, 'w', encoding='utf-8') as file:
        if ext == '.csv':
            # Convert the result dict to CSV format
            # Assuming result is a list of dictionaries
            writer = csv.DictWriter(file, fieldnames=crush(result[0]).keys())
            await writer.writeheader()
            for row in result:
                flat_row = crush(row)
                await writer.writerow(flat_row)
        elif ext == '.yml' or ext == '.yaml':
            # Convert the result dict to YAML format
            yaml_data = yaml.dump(result, allow_unicode=True)
            await file.write(yaml_data)
        else:  # Default to JSON
            await file.write(json.dumps(result, ensure_ascii=False))

async def weave_entry(data, config, *args, **kwargs):
    """
    Weaves the data with the given configuration.

    Args:
        data (dict): The input data.
        config (dict): The configuration.

    Returns:
        dict: The weaved data.
    """
    await load_config(config)
    result = await process_entry(data)

    if 'file_path' in kwargs and isinstance(kwargs['file_path'], str):
        await save_result_to_file(result, kwargs['file_path'])

    return result

async def weave_entries(data: list[dict], config: dict, *args, **kwargs):
    """
    Weaves the data with the given configuration.

    Args:
        data (dict): The input data.
        config (dict): The configuration.

    Returns:
        dict: The weaved data.
    """
    await load_config(config)
    result = await process_entries(data)

    if 'file_path' in kwargs and isinstance(kwargs['file_path'], str):
        await save_result_to_file(result, kwargs['file_path'])

    return result
