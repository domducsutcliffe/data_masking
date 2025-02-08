import json
from typeguard import typechecked
from typing import Any

@typechecked
def json_checker(obfuscation_config: str):
    try:
        json.loads(obfuscation_config)
        return True
    except json.JSONDecodeError:
        raise