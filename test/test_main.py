import json
import pytest
from src.main import json_checker
from typeguard import TypeCheckError

def test_json_checker_no_args():
    with pytest.raises(TypeError, match=r"missing 1 required positional argument: 'obfuscation_config'"):
        json_checker()

@pytest.mark.parametrize("bad_arg", [
    [1, 2, 3],
    (1, 2, 3),
    42,
])
def test_detect_incorrect_data_type_argument(bad_arg):
    with pytest.raises(TypeCheckError):
        json_checker(bad_arg)

def test_valid_json():
    valid = '{"file_to_obfuscate": "s3://your_bucket/path/file.csv", "pii_fields": ["name", "email_address"]}'
    assert json_checker(valid)

def test_malformed_json():
    malformed = '{"file_to_obfuscate": "s3://your_bucket/path/file.csv", "pii_fields": ["name", "email_address"]'
    with pytest.raises(json.decoder.JSONDecodeError):
        json_checker(malformed)
