import json
import pytest
from src.main import json_checker
from typeguard import TypeCheckError

class TestJSON:
    def test_json_checker_no_args(self):
        with pytest.raises(TypeError):
            json_checker()

    @pytest.mark.parametrize("bad_arg", [
        [1, 2, 3],
        (1, 2, 3),
        42,
    ])
    def test_detect_incorrect_data_type_argument(self, bad_arg):
        with pytest.raises(TypeCheckError):
            json_checker(bad_arg)

    def test_valid_json(self):
        valid = '{"file_to_obfuscate": "s3://your_bucket/path/file.csv", "pii_fields": ["name", "email_address"]}'
        assert json_checker(valid)

    def test_malformed_json(self):
        malformed = '{"file_to_obfuscate": "s3://your_bucket/path/file.csv", "pii_fields": ["name", "email_address"]'
        with pytest.raises(json.decoder.JSONDecodeError):
            json_checker(malformed)

    def test_incorrect_json_keys(self):
        malformed = '{"foo": "s3://your_bucket/path/file.csv", "bar": ["name", "email_address"]}'
        with pytest.raises(ValueError):
            json_checker(malformed)

    def test_malformed_s3_uri(self):
        http_object = '{"file_to_obfuscate": "https://your_bucket/path/file.csv", "pii_fields": ["name", "email_address"]}'
        with pytest.raises(ValueError):
            json_checker(http_object)


