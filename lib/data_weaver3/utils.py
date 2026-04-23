def crush(nested_dict: dict | list, parent_key: str = '', sep: str = '.') -> dict:
    """Flatten a nested dict/list into a single-level dict with dotted keys.

    Lists produce numeric path segments: ``{"a": [1, 2]} -> {"a.0": 1, "a.1": 2}``.

    Args:
        nested_dict: The nested structure to flatten.
        parent_key: Prefix applied to keys at this recursion level (internal).
        sep: Separator used between path segments.

    Returns:
        A flat dict keyed by dotted paths.
    """
    items = []
    if isinstance(nested_dict, list):
        for i, value in enumerate(nested_dict):
            new_key = f"{parent_key}{sep}{i}" if parent_key else str(i)
            if isinstance(value, (dict, list)):
                items.extend(crush(value, new_key, sep=sep).items())
            else:
                items.append((new_key, value))
    elif isinstance(nested_dict, dict):
        for key, value in nested_dict.items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else key
            if isinstance(value, (dict, list)):
                items.extend(crush(value, new_key, sep=sep).items())
            else:
                items.append((new_key, value))
    return dict(items)


def construct(flat_dict: dict) -> dict:
    """Rebuild a nested dict/list from a flat dict with dotted keys.

    Inverse of :func:`crush`. Numeric path segments become list indices;
    non-numeric segments become dict keys.

    Args:
        flat_dict: Flat mapping keyed by dotted paths.

    Returns:
        The reconstructed nested structure.
    """
    def recursive_construct(paths, value, base):
        if len(paths) == 1:
            if isinstance(base, list):
                index = int(paths[0])
                while len(base) <= index:
                    base.append(None)
                base[index] = value
            else:
                base[paths[0]] = value
            return

        current_path, rest_paths = paths[0], paths[1:]
        is_index = current_path.isdigit()

        if is_index:
            current_path = int(current_path)
            while len(base) <= current_path:
                base.append([] if rest_paths and rest_paths[0].isdigit() else {})
            next_base = base[current_path]
        else:
            if current_path not in base:
                base[current_path] = [] if rest_paths and rest_paths[0].isdigit() else {}
            next_base = base[current_path]

        recursive_construct(rest_paths, value, next_base)

    result: dict = {}
    for key, value in flat_dict.items():
        recursive_construct(key.split('.'), value, result)
    return result
