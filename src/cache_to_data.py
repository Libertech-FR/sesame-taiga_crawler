import asyncio
import json
from pathlib import Path

import yaml
from lib.data_weaver3 import weave_entry


def load_transform_configs(config_path: Path) -> dict:
    with config_path.open("r", encoding="utf-8") as fh:
        docs = [doc for doc in yaml.safe_load_all(fh) if doc is not None]

    if not docs:
        return {}

    if len(docs) == 1:
        if not isinstance(docs[0], dict):
            raise ValueError(f"Invalid config format in {config_path}: expected mapping")
        return docs[0]

    merged: dict = {}
    for idx, doc in enumerate(docs, start=1):
        if not isinstance(doc, dict):
            raise ValueError(f"Invalid config format in {config_path} (document #{idx}): expected mapping")
        merged.update(doc)
    return merged


async def convert_cache_file_to_data(cache_file: Path, config: dict) -> list[dict]:
    payload = json.loads(cache_file.read_text(encoding="utf-8"))
    entries = payload.get("data", [])
    result: list[dict] = []
    for entry in entries:
        result.append(weave_entry(entry, config))
    return result


async def convert_cache_dir_to_data(cache_dir: Path, output_dir: Path, config_path: Path) -> list[Path]:
    configs = load_transform_configs(config_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_files: list[Path] = []

    for cache_file in sorted(cache_dir.glob("taiga_*.json")):
        if cache_file.name not in configs:
            continue
        converted = await convert_cache_file_to_data(cache_file, configs[cache_file.name])
        output_file = output_dir / cache_file.name
        output_file.write_text(json.dumps(converted, ensure_ascii=False, indent=4), encoding="utf-8")
        output_files.append(output_file)

    return output_files


def run_conversion(cache_dir: str, output_dir: str, config_path: str = "./config.yml") -> list[Path]:
    return asyncio.run(
        convert_cache_dir_to_data(
            cache_dir=Path(cache_dir),
            output_dir=Path(output_dir),
            config_path=Path(config_path),
        )
    )
