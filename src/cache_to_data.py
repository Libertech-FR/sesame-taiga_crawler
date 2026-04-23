import asyncio
import json
from pathlib import Path

import yaml
from lib.data_weaver3 import weave_entry


def load_transform_configs(config_path: Path) -> dict:
    with config_path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


async def convert_cache_file_to_data(cache_file: Path, config: dict) -> list[dict]:
    payload = json.loads(cache_file.read_text(encoding="utf-8"))
    entries = payload.get("data", [])
    result: list[dict] = []
    for entry in entries:
        result.append(await weave_entry(entry, config))
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
