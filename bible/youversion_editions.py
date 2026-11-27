"""Stable identities and previously verified numbering; never infer from labels."""

import json
from pathlib import Path
from typing import cast

# Compatibility assignments for previously installed editions. New editions
# follow the verified source-index path and never add an assignment here.
EDITIONS = {
    int(identifier): cast("tuple[str, str, str]", tuple(fields))
    for identifier, fields in json.loads(
        Path(__file__).with_name("youversion_legacy_numbering.json").read_text()
    )["editions"].items()
}
METADATA_URL = "https://nodejs.bible.com/api/bible/version/3.3?id={edition}"
CONFIGURATION_URL = "https://bible.youversionapi.com/3.1/configuration.json"
VERSIONS_URL = "https://bible.youversionapi.com/3.1/versions.json?language_tag={language}&type=all"


def module_id(edition: int) -> str:
    """Validate a provider edition ID and produce its stable local module name."""
    if type(edition) is not int or not 1 <= edition <= 999999999:
        raise ValueError("Invalid edition identity")
    return "YV" + str(edition)


def edition_id(name: str) -> int:
    """Parse a canonical local module name, rejecting ambiguous numeric spellings."""
    if not isinstance(name, str) or not name.startswith("YV") or not name[2:].isdigit():
        raise ValueError("Invalid edition identity")
    number = int(name[2:])
    if module_id(number) != name:
        raise ValueError("Invalid edition identity")
    return number


def storage_system(identifier: int) -> str:
    """Use verified numbering metadata; keep unverified editions independently indexed."""
    module_id(identifier)
    # Keep every existing module and annotation reference stable. New editions
    # receive an exact source-specific index, not an assumed cross-edition map.
    return EDITIONS[identifier][1] if identifier in EDITIONS else "YouVersion" + str(identifier)
