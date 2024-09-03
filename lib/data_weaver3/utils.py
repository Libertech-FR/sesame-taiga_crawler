def crush(nested_dict, parent_key='', sep='.'):
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

def construct(flat_dict):
    def recursive_construct(paths, value, base, depth=0):
        # Debug output setup
        indent = "  " * depth

        # Base case: set the value at the end of the path
        if len(paths) == 1:
            if isinstance(base, list):
                index = int(paths[0])
                # Ensure the list is long enough
                while len(base) <= index:
                    base.append(None)
                base[index] = value
            else:
                base[paths[0]] = value
            return

        # Determine the current path part and whether it's an index for a list
        current_path, rest_paths = paths[0], paths[1:]
        is_index = current_path.isdigit()

        # Prepare the next level base (either dict or list)
        if is_index:
            current_path = int(current_path)
            # Ensure the list is long enough and correctly initialized
            while len(base) <= current_path:
                base.append([] if rest_paths and rest_paths[0].isdigit() else {})
            next_base = base[current_path]
        else:
            if current_path not in base:
                base[current_path] = [] if rest_paths and rest_paths[0].isdigit() else {}
            next_base = base[current_path]

        # Recursive call to construct the next level
        recursive_construct(rest_paths, value, next_base, depth + 1)

    # Root of the constructed structure
    result = {}
    for key, value in flat_dict.items():
        paths = key.split('.')
        recursive_construct(paths, value, result)
    return result