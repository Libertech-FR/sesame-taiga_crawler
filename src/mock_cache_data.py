import argparse
import json
import random
import re
from datetime import date
from pathlib import Path
from typing import Any


def load_cache_payload(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _random_date(rng: random.Random) -> str:
    year = rng.randint(1990, date.today().year + 2)
    month = rng.randint(1, 12)
    day = rng.randint(1, 28)
    return f"{day:02d}/{month:02d}/{year}"


def _randomized_string(value: str, key: str, rng: random.Random) -> str:
    if value == "":
        return ""

    if re.fullmatch(r"\d{2}/\d{2}/\d{4}", value):
        return _random_date(rng)

    if key.lower() in {"email1", "email2"} and "@" in value:
        local, domain = value.split("@", 1)
        return f"{local}{rng.randint(10, 99)}@{domain}"

    # Ex: adm-174.jpg, etd-112018.jpg
    image_match = re.fullmatch(r"([a-z]{3}-)\d+(\.jpg)", value)
    if image_match:
        prefix, suffix = image_match.groups()
        return f"{prefix}{rng.randint(100, 999999)}{suffix}"

    # Replace digit groups while keeping human-readable format.
    if re.search(r"\d", value):
        return re.sub(r"\d+", lambda m: str(rng.randint(1, 10 ** len(m.group(0)) - 1)).zfill(len(m.group(0))), value)

    return value


def _generate_scalar(samples: list[Any], key: str, rng: random.Random) -> Any:
    non_null = [item for item in samples if item is not None]
    if not non_null:
        return None

    base = rng.choice(non_null)

    if isinstance(base, bool):
        return rng.choice([True, False])
    if isinstance(base, int):
        minimum = min(int(x) for x in non_null if isinstance(x, int))
        maximum = max(int(x) for x in non_null if isinstance(x, int))
        if minimum == maximum:
            return minimum
        return rng.randint(minimum, maximum)
    if isinstance(base, float):
        minimum = min(float(x) for x in non_null if isinstance(x, (float, int)))
        maximum = max(float(x) for x in non_null if isinstance(x, (float, int)))
        if minimum == maximum:
            return minimum
        return round(rng.uniform(minimum, maximum), 2)
    if isinstance(base, str):
        return _randomized_string(base, key, rng)

    return base


def _generate_entry(samples: list[dict[str, Any]], rng: random.Random) -> dict[str, Any]:
    keys: set[str] = set()
    for sample in samples:
        keys.update(sample.keys())

    generated: dict[str, Any] = {}
    for key in sorted(keys):
        key_samples = [entry.get(key) for entry in samples]
        generated[key] = _generate_scalar(key_samples, key, rng)
    return generated


def generate_mock_from_cache_payload(payload: dict[str, Any], size: int = 10, seed: int | None = None) -> dict[str, Any]:
    if "data" not in payload or not isinstance(payload["data"], list):
        raise ValueError("Le payload doit contenir une clé 'data' de type liste")

    rng = random.Random(seed)
    data = payload["data"]
    if not data:
        return {
            "type": payload.get("type", "unknown"),
            "data": [],
            "total": 0,
        }

    if not isinstance(data[0], dict):
        raise ValueError("La clé 'data' doit contenir des objets")

    generated_data = [_generate_entry(data, rng) for _ in range(size)]
    return {
        "type": payload.get("type", "unknown"),
        "data": generated_data,
        "total": len(generated_data),
    }


def generate_mocks_from_cache_dir(cache_dir: Path, output_dir: Path, size: int = 10, seed: int | None = None) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_files: list[Path] = []

    json_files = sorted(cache_dir.glob("taiga_*.json"))
    for file_path in json_files:
        payload = load_cache_payload(file_path)
        mock_payload = generate_mock_from_cache_payload(payload, size=size, seed=seed)
        output_path = output_dir / file_path.name
        with output_path.open("w", encoding="utf-8") as fh:
            json.dump(mock_payload, fh, ensure_ascii=False, indent=4)
        generated_files.append(output_path)

    return generated_files


def main() -> None:
    parser = argparse.ArgumentParser(description="Génère des mocks aléatoires depuis cache/*.json")
    parser.add_argument("--cache-dir", default="./cache", help="Dossier des fichiers cache source")
    parser.add_argument("--output-dir", default="./cache/mocks", help="Dossier de sortie des mocks")
    parser.add_argument("--size", type=int, default=10, help="Nombre d'entrées par fichier mock")
    parser.add_argument("--seed", type=int, default=None, help="Seed aléatoire (optionnel)")
    args = parser.parse_args()

    generated = generate_mocks_from_cache_dir(
        cache_dir=Path(args.cache_dir),
        output_dir=Path(args.output_dir),
        size=args.size,
        seed=args.seed,
    )
    print(f"{len(generated)} fichier(s) mock généré(s)")


if __name__ == "__main__":
    main()
