
import re
from typing import Any, Callable, Dict
import unicodedata

def apply_to_value(value, func, *args, **kwargs):
    if isinstance(value, dict):
        return {key: apply_to_value(val, func, *args, **kwargs) for key, val in value.items()}
    elif isinstance(value, list):
        return [apply_to_value(val, func, *args, **kwargs) for val in value]
    else:
        return func(value, *args, **kwargs)

def capitalize(value: str) -> str:
    def capitalize_val(val):
        return val.capitalize()
    return apply_to_value(value, capitalize_val)

def concat(values: list, delimiter=' ') -> str:
    if all(isinstance(value, str) for value in values):
        return delimiter.join(values)
    else:
        raise TypeError("All values in concat must be strings")

def parse_type(value, typename: str) -> type:
    try:
        # Mapping string to actual type
        type_map = {
            "int": int,
            "float": float,
            "str": str,
            "bool": lambda x: x.lower() in ['true', '1', 't', 'yes', 'y']
        }
        def parse(val):
            return type_map[typename](val)
        return apply_to_value(value, parse)
    except KeyError:
        raise ValueError(f"Invalid type {typename}")

def prefix(value: str | list | dict, prefix: str) -> str:
    def prefix_val(val):
        return f"{prefix}{val}"
    return apply_to_value(value, prefix_val)

def suffix(value: str | list | dict, suffix: str) -> str:
    def suffix_val(val):
        return f"{val}{suffix}"
    return apply_to_value(value, suffix_val)

def split(value: str, delimiter: str = ' ') -> list:
    return value.split(delimiter)

def joinStr(values: list, delimiter: str = ' ') -> str:
    print('test jointure xxxxxxxxxxxxxxxxxxxxxxxxx ')
    r=[]
    for v in values:
        if type(v) is None:
            r.append(r)
        else:
            r.append(v)

    values = [str(value) if value is not None else '' for value in values]
    return delimiter.join(r)

def lower(value: str | list | dict) -> str:
    def lower_val(val):
        return val.lower()
    return apply_to_value(value, lower_val)

def title(value: str | list | dict) -> str:
    def title_val(val):
        return val.title()
    return apply_to_value(value, title_val)

def upper(value: str | list | dict) -> str:
    def upper_val(val):
        return val.upper()
    return apply_to_value(value, upper_val)

def replace(value: str | list | dict, old: str, new: str) -> str:
    def replace_val(val):
        return val.replace(old, new)
    return apply_to_value(value, replace_val)

def regex(value: str | list | dict, pattern: str, replace: str) -> str:
    def regex_replace(val):
        return re.sub(pattern, replace, val)
    return apply_to_value(value, regex_replace)

def remove_accents(value: str) -> str:
        def remove_accents_val(val):
            return ''.join(c for c in unicodedata.normalize('NFD', val) if unicodedata.category(c) != 'Mn')
        return apply_to_value(value, remove_accents_val)

TRANSFORMATIONS: Dict[str, Callable[..., Any]] = {
    "capitalize": capitalize,
    "lower": lower,
    "title": title,
    "upper": upper,
    "remove_accents": remove_accents,
    "concat": lambda value, delimiter='': concat(value, delimiter),
    "parse_type": lambda value, typename: parse_type(value, typename),
    "prefix": lambda value, string: prefix(value, string),
    "suffix": lambda value, string: suffix(value, string),
    "split": lambda value, delimiter=None: split(value, delimiter),
    "join": lambda value, delimiter='': joinStr(value, delimiter),
    "replace": lambda value, old, new: replace(value, old, new),
    "regex": lambda value, pattern, replace: regex(value, pattern, replace),
}

def parse_args(args: str) -> dict:
    kwargs = {}

    # Regex pattern to match key-value pairs considering nested structures and quoted strings
    pattern = re.compile(r"(\w+)=('(?:\\.|[^'])*'|\"(?:\\.|[^\"])*\"|\([^)]*\)|\[[^\]]*\]|\{[^}]*\}|\S+)")

    for match in pattern.finditer(args):
        key = match.group(1).strip()
        value = match.group(2).strip()

        # Remove the outer quotes from strings, if they exist
        if value.startswith(("'", '"')) and value.endswith(("'", '"')):
            value = value[1:-1]
        else:
            # Try to parse the value using ast.literal_eval for safety
            try:
                value = ast.literal_eval(value)
            except (ValueError, SyntaxError):
                # If parsing fails, keep the value as a string
                value = str(value)

        kwargs[key] = value

    return kwargs

def parse_function_call(call_str):
    # Define the regex pattern
    pattern = re.compile(r"(\w+)(?:\((.*)\))?")
    match = pattern.match(call_str)

    if not match:
        print(f"Invalid function call: {call_str}")

    func_name = match.group(1)
    args_str = match.group(2)

    if args_str is None:
        # No arguments, return empty list for args
        return func_name, {}

    kwargs = parse_args(args_str)
    return func_name, kwargs

def parse_transform(transform: str, value: Any) -> Any:
    # func_name, *args = transform.replace(")", "").split("(")
    func_name, kwargs = parse_function_call(transform)
    func = TRANSFORMATIONS.get(func_name)
    if not func:
        print(f"Invalid transform function: {func_name} for value: {value}")
        return value
    try :
        # kwargs = parse_args(args)
        return func(value, **kwargs)
    except Exception as e:
        print(e)
        print(f"Error in transform function: {func_name} for value: {value} with args: {kwargs}")
        return value
