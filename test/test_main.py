import pytest
from src.main import json_checker
import sys
from typeguard import TypeCheckError

def test_json_checker_no_args():
    with pytest.raises(TypeError, match=r"missing 1 required positional argument: 'obfuscation_config'"):
        json_checker()

@pytest.mark.parametrize("bad_arg", [
    "a string",
    [1, 2, 3],
    (1, 2, 3),
    42,
])
def test_detect_incorrect_data_type_argument(bad_arg):
    with pytest.raises(TypeCheckError):
        json_checker(bad_arg)