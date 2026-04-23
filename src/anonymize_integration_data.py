import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cache_to_data import run_conversion


ID_KEYS = ("id_etd", "id_ens", "id_adm", "id_coord")


def _stable_token(scope: str, ref: str, size: int = 10) -> str:
    return hashlib.sha1(f"{scope}:{ref}".encode("utf-8")).hexdigest()[:size]


def _person_ref(entry: dict[str, Any]) -> str:
    for key in ID_KEYS:
        value = entry.get(key)
        if value is not None:
            return str(value)
    return _stable_token("entry", json.dumps(entry, sort_keys=True, ensure_ascii=False), 12)


def _fake_date(ref: str) -> str:
    h = int(_stable_token("date", ref, 8), 16)
    day = (h % 28) + 1
    month = ((h // 29) % 12) + 1
    year = 1970 + ((h // 353) % 35)
    return f"{day:02d}/{month:02d}/{year}"


def _fake_phone(ref: str, mobile: bool = True) -> str:
    digits = "".join(str((int(c, 16) % 10)) for c in _stable_token("tel", ref, 8))
    prefix = "06" if mobile else "04"
    return f"{prefix} {digits[0:2]} {digits[2:4]} {digits[4:6]} {digits[6:8]}"


def _fake_zip(ref: str) -> str:
    num = int(_stable_token("zip", ref, 4), 16) % 90000 + 10000
    return str(num)


def _fake_email(ref: str, domain: str = "example.test") -> str:
    return f"user-{_stable_token('mail', ref, 8)}@{domain}"


def _anonymize_value(key: str, value: Any, ref: str) -> Any:
    if value in ("", None):
        return value

    low_key = key.lower()
    if low_key in {"nom", "nom_usage", "nom_marital"}:
        return f"Nom-{_stable_token(low_key, ref, 6)}"
    if low_key == "prenom":
        return f"Prenom-{_stable_token(low_key, ref, 6)}"
    if low_key in {"adresse"}:
        return f"{int(_stable_token('addrn', ref, 3), 16) % 300 + 1} rue de Test"
    if low_key in {"ville"}:
        return f"Ville-{_stable_token('city', ref, 4)}"
    if low_key in {"cp"}:
        return _fake_zip(ref)
    if low_key in {"email1", "email2"}:
        return _fake_email(ref if low_key == "email1" else f"{ref}:perso")
    if low_key in {"login"}:
        return f"user{_stable_token('uid', ref, 6)}"
    if low_key in {"tel_mob", "tel_portable"}:
        return _fake_phone(ref, mobile=True)
    if low_key in {"tel_fixe"}:
        return _fake_phone(ref, mobile=False)
    if low_key in {"nss_date"}:
        return _fake_date(ref)
    if low_key in {"nss_ville"}:
        return f"Ville-{_stable_token('birthcity', ref, 4)}"
    if low_key in {"num_ine"}:
        return f"{_stable_token('ine', ref, 10).upper()}AA"
    if low_key in {"num_etd", "codebarre"}:
        return str(int(_stable_token(low_key, ref, 5), 16) % 100000).zfill(5)
    if low_key in {"mot_de_passe"}:
        return hashlib.sha1(f"pwd:{ref}".encode("utf-8")).hexdigest()
    if low_key in {"mot_de_passe_ldap"}:
        return "{SHA}" + _stable_token("ldap", ref, 28)
    if low_key in {"carte_num_regional", "carte_num_local"}:
        return _stable_token(low_key, ref, 14)
    if low_key in {"photo_nom"} and isinstance(value, str):
        match = re.fullmatch(r"([a-z]{3}-)\d+(\.jpg)", value)
        if match:
            return f"{match.group(1)}{int(_stable_token('photo', ref, 6), 16) % 999999}{match.group(2)}"
    return value


def anonymize_cache_payload(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data")
    if not isinstance(data, list):
        return payload

    new_data: list[dict[str, Any]] = []
    for entry in data:
        if not isinstance(entry, dict):
            new_data.append(entry)
            continue
        ref = _person_ref(entry)
        cleaned = {k: _anonymize_value(k, v, ref) for k, v in entry.items()}
        new_data.append(cleaned)

    out = dict(payload)
    out["data"] = new_data
    out["total"] = len(new_data)
    return out


def anonymize_cache_dir(cache_dir: Path) -> list[Path]:
    written: list[Path] = []
    for src in sorted(cache_dir.glob("taiga_*.json")):
        payload = json.loads(src.read_text(encoding="utf-8"))
        anonymized = anonymize_cache_payload(payload)
        src.write_text(json.dumps(anonymized, ensure_ascii=False, indent=4), encoding="utf-8")
        written.append(src)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Anonymise tests_integration/cache puis régénère tests_integration/data")
    parser.add_argument("--cache-dir", default="./tests_integration/cache")
    parser.add_argument("--data-dir", default="./tests_integration/data")
    parser.add_argument("--config", default="./config.yml")
    args = parser.parse_args()

    cache_dir = Path(args.cache_dir)
    data_dir = Path(args.data_dir)
    config_path = Path(args.config)

    anonymized_files = anonymize_cache_dir(cache_dir)
    converted_files = run_conversion(str(cache_dir), str(data_dir), str(config_path))

    print(f"{len(anonymized_files)} fichier(s) cache anonymisé(s)")
    print(f"{len(converted_files)} fichier(s) data régénéré(s)")


if __name__ == "__main__":
    main()
