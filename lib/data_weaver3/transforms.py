import logging
import re
import typing
import unicodedata
from typing import Any, Callable, Dict

logger = logging.getLogger(__name__)

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

def parse_type(value, typename: str) -> Any:
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

def prefix(value: typing.Union[str,list,dict], string: str) -> str:
    def prefix_val(val):
        return f"{string}{val}"
    return apply_to_value(value, prefix_val)

def suffix(value: typing.Union[str,list,dict], string: str) -> str:
    def suffix_val(val):
        return f"{val}{string}"
    return apply_to_value(value, suffix_val)

def split(value: str, delimiter: str = ' ') -> list:
    return value.split(delimiter)

def join(values: list, delimiter: str = ' ') -> str:
    return delimiter.join(str(v) for v in values if v is not None and v != '')

def lower(value: typing.Union[str,list,dict]) -> str:
    def lower_val(val):
        return val.lower()
    return apply_to_value(value, lower_val)

def title(value: typing.Union[str,list,dict]) -> str:
    def title_val(val):
        return val.title()
    return apply_to_value(value, title_val)

def upper(value:typing.Union[str,list,dict]) -> str:
    def upper_val(val):
        return val.upper()
    return apply_to_value(value, upper_val)

def replace(value: typing.Union[str,list,dict], old: str, new: str) -> str:
    def replace_val(val):
        return val.replace(old, new)
    return apply_to_value(value, replace_val)

def regex(value: typing.Union[str,list,dict], pattern: str, replace: str) -> str:
    def regex_replace(val):
        return re.sub(pattern, replace, val)
    return apply_to_value(value, regex_replace)

def remove_accents(value: str) -> str:
        def remove_accents_val(val):
            return ''.join(c for c in unicodedata.normalize('NFD', val) if unicodedata.category(c) != 'Mn')
        return apply_to_value(value, remove_accents_val)

def substr(value : typing.Union[str,list,dict], start:int, end:int)->str:
    def substr_val(val):
        return val[start:end]
    return apply_to_value(value,substr_val)

TRANSFORMATIONS: Dict[str, Callable[..., Any]] = {
    "capitalize": capitalize,
    "lower": lower,
    "title": title,
    "upper": upper,
    "remove_accents": remove_accents,
    "concat": concat,
    "parse_type": parse_type,
    "prefix": prefix,
    "suffix": suffix,
    "split": split,
    "join": join,
    "replace": replace,
    "regex": regex,
    "substr": substr
}

def parse_args(args: str) -> dict:
    if args is None or args.strip() == "":
        return {}
    kwargs = {}
    # Support:
    # - comma separated kwargs: pattern='x', replace='y'
    # - space separated kwargs: start=1 end=3
    token_pattern = re.compile(
        r"(\w+)\s*=\s*(.+?)(?:(?:\s*,\s*|\s+)(?=\w+\s*=)|$)"
    )

    for match in token_pattern.finditer(args):
        key = match.group(1).strip()
        value = match.group(2).strip()
        if not key:
            continue

        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
            kwargs[key] = value
            continue

        if value == "":
            kwargs[key] = ""
            continue

        lower_value = value.lower()
        if lower_value in {"true", "false"}:
            kwargs[key] = lower_value == "true"
            continue

        if re.fullmatch(r"-?\d+", value):
            kwargs[key] = int(value)
            continue

        if re.fullmatch(r"-?\d+\.\d+", value):
            kwargs[key] = float(value)
            continue

        kwargs[key] = value

    return kwargs

def parse_function_call(call_str: str) -> tuple[str, dict]:
    match = re.compile(r"(\w+)(?:\((.*)\))?").match(call_str)
    if not match:
        raise ValueError(f"Invalid function call: {call_str!r}")
    func_name = match.group(1)
    args_str = match.group(2)
    return func_name, (parse_args(args_str) if args_str is not None else {})

def parse_transform(transform: str, value: Any) -> Any:
    func_name, kwargs = parse_function_call(transform)
    func = TRANSFORMATIONS.get(func_name)
    if not func:
        logger.warning("Unknown transform %r; passing value through", func_name)
        return value
    try:
        return func(value, **kwargs)
    except (TypeError, ValueError, KeyError, re.error) as e:
        logger.warning("Transform %s(%r) on %r failed: %s", func_name, kwargs, value, e)
        return value
