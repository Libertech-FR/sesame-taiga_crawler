import csv
import json
import logging
import os

import yaml

from lib.data_weaver3.transforms import parse_transform
from lib.data_weaver3.utils import construct, crush

logger = logging.getLogger(__name__)


def _validate_config(cfg: dict) -> dict:
    """Validate a config dict in place.

    Ensures `mapping` is present and defaults `additionalFields` to `{}`.

    Args:
        cfg: The configuration dict to validate.

    Returns:
        dict: The same dict, with `additionalFields` defaulted if missing.

    Raises:
        ValueError: If `mapping` is missing.
    """
    if cfg.get('mapping') is None:
        raise ValueError("Invalid config: missing 'mapping'")
    cfg.setdefault('additionalFields', {})
    return cfg


def _load_config_from_disk() -> dict:
    """Load a YAML config from the path given by CONFIG_FILE_TRANSFORM (or ./config/config.yml)."""
    path = os.getenv('CONFIG_FILE_TRANSFORM', './config/config.yml')
    with open(path, 'r', encoding='utf8') as fh:
        return yaml.safe_load(fh)


def _resolve_config(config: dict | None) -> dict:
    """Return a validated copy of the config, loading from disk when None.

    The returned dict is a shallow copy — callers can pass their own config without
    risking mutation from downstream helpers.
    """
    if config is None:
        config = _load_config_from_disk()
    return _validate_config(dict(config))


def _handle_value(data: dict, source_key, target_key: str, config: dict, default: bool = False):
    """Resolve the value for the given target_key from data, dispatching on source_key shape.

    Args:
        data: The flattened input dictionary.
        source_key (str | dict | list): The key(s) to read from data. When a dict, the
            returned value is a dict of sub-results; when a list, a list of sub-results.
        target_key: The target key being written to — used to look up transforms/defaults.
        config: The resolved configuration.
        default: When True, missing/falsy values fall back to the configured default.

    Returns:
        Any: The resolved (and optionally transformed) value.
    """
    def get_value_with_default(src_key):
        """Return (value, is_default) for a single source key."""
        value = data.get(src_key)
        if not value and default:
            return _handle_default_value(data, target_key, config), True
        return value, False

    def handle_dict(src: dict):
        """Handle a dict-shaped source_key: {sub_key: value, ...}."""
        handled = {sub: get_value_with_default(sub)[0] for sub in src}
        is_default = any(get_value_with_default(sub)[1] for sub in src)
        if is_default:
            return handled
        return _transform_value(handled, target_key, config)

    def handle_list(src: list):
        """Handle a list-shaped source_key: [value_for_sub_key_0, value_for_sub_key_1, ...]."""
        handled = [get_value_with_default(sub)[0] for sub in src]
        is_default = all(get_value_with_default(sub)[1] for sub in src)
        if is_default:
            return handled
        return _transform_value(handled, target_key, config)

    def handle_scalar(src):
        """Handle a scalar source_key (plain string)."""
        handled, is_default = get_value_with_default(src)
        if is_default:
            return handled
        return _transform_value(handled, target_key, config)

    if isinstance(source_key, dict):
        return handle_dict(source_key)
    if isinstance(source_key, list):
        return handle_list(source_key)
    return handle_scalar(source_key)


def _handle_default_value(data: dict, target_key: str, config: dict):
    """Resolve the default value for target_key from the config's `default` section.

    Prefers `default.dynamic` (a source key to read from data, then transform) over
    `default.static` (a literal value). Returns None when neither is configured.
    """
    dynamic_key = config.get('default', {}).get('dynamic', {}).get(target_key)
    if dynamic_key is not None:
        value = _handle_value(data, dynamic_key, target_key, config, False)
        return _transform_value(value, target_key, config, True)

    static_value = config.get('default', {}).get('static', {}).get(target_key)
    if static_value is not None:
        return static_value

    return None


def _transform_value(value, field: str, config: dict, default: bool = False):
    """Apply the configured transform(s) for the given field to value.

    Args:
        value: The value to transform.
        field: The target field name (key into `config['transforms']`).
        config: The resolved configuration.
        default: When True, reads from `config['default']['transforms']` instead.

    Returns:
        Any: The transformed value, or value unchanged when no transform is configured.
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


def _map_fields(data: dict, final_result: dict, config: dict) -> None:
    """Populate final_result from data using config['mapping'] and config['additionalFields']."""
    for target_key, source_key in config['mapping'].items():
        final_result[target_key] = _handle_value(data, source_key, target_key, config)

    for target_key, value in config['additionalFields'].items():
        final_result[target_key] = value


def _process_entry(entry: dict, config: dict) -> dict:
    """Crush entry, map its fields, reconstruct a nested dict."""
    final_result: dict = {}
    _map_fields(crush(entry), final_result, config)
    return construct(final_result)


def _process_entries(entries: list[dict], config: dict) -> list[dict]:
    """Apply _process_entry to each entry."""
    return [_process_entry(entry, config) for entry in entries]


def save_result_to_file(result, file_path: str) -> None:
    """Serialize result to disk; format is inferred from the file extension.

    Supported extensions: .csv, .json, .yml, .yaml. Any other extension triggers a
    warning and is written as JSON (with .json appended to the path to avoid
    silently writing under the wrong extension).

    For CSV, records are flattened via crush() and the header is the union of keys
    across all rows (so sparse records don't lose columns).
    """
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    if ext not in {'.csv', '.json', '.yml', '.yaml'}:
        logger.warning("Invalid file extension %r; defaulting to JSON", ext)
        ext = '.json'
        file_path = f"{file_path}.json"

    if ext == '.csv':
        rows = result if isinstance(result, list) else [result]
        flat_rows = [crush(row) for row in rows]
        if not flat_rows:
            open(file_path, 'w').close()
            return
        fieldnames = sorted({k for r in flat_rows for k in r})
        with open(file_path, 'w', newline='', encoding='utf-8') as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(flat_rows)
        return

    with open(file_path, 'w', encoding='utf-8') as fh:
        if ext in {'.yml', '.yaml'}:
            yaml.dump(result, fh, allow_unicode=True)
        else:
            json.dump(result, fh, ensure_ascii=False)


def weave_entry(data: dict, config: dict | None = None, *, file_path: str | None = None) -> dict:
    """Weave a single entry through the configured mapping and transforms.

    Args:
        data: The input record.
        config: The transformation config. When None, it's loaded from the path in
            the CONFIG_FILE_TRANSFORM env var (default ./config/config.yml).
        file_path: Optional output path — when set, the result is also written to
            disk via save_result_to_file().

    Returns:
        dict: The woven (mapped + transformed + reconstructed) record.
    """
    cfg = _resolve_config(config)
    result = _process_entry(data, cfg)
    if file_path:
        save_result_to_file(result, file_path)
    return result


def weave_entries(data: list[dict], config: dict | None = None, *, file_path: str | None = None) -> list[dict]:
    """Weave a list of entries. See weave_entry() for argument semantics.

    Returns:
        list[dict]: The list of woven records, in input order.
    """
    cfg = _resolve_config(config)
    result = _process_entries(data, cfg)
    if file_path:
        save_result_to_file(result, file_path)
    return result
