import json
import pandas as pd
import pytest
from src.main import json_checker, obfuscate
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

class Testobfuscate:
    def test_obfuscate_with_no_pii_fields(self):
        df = pd.DataFrame({
            'name': ['Alice', 'Bob'],
            'age': [25, 30],
            'email': ['alice@example.com', 'bob@example.com']
        })

        pii_fields = []
        obfuscated_df = obfuscate(pii_fields, df.copy())

        assert all(obfuscated_df['name'] == df['name'])
        assert all(obfuscated_df['email'] == df['email'])
        assert all(obfuscated_df['age'] == df['age'])

    def test_obfuscate_with_two_pii_fields(self):
        df = pd.DataFrame({
            'name': ['Alice', 'Bob'],
            'age': [25, 30],
            'email': ['alice@example.com', 'bob@example.com']
        })

        pii_fields = ['name', 'email']
        obfuscated_df = obfuscate(pii_fields, df.copy())

        assert all(obfuscated_df['name'] == '***')
        assert all(obfuscated_df['email'] == '***')
        assert all(obfuscated_df['age'] == df['age'])
    
    def test_obfuscate_with_invalid_pii_fields_only(self):
        df = pd.DataFrame({
            'name': ['Alice', 'Bob'],
            'age': [25, 30],
            'email': ['alice@example.com', 'bob@example.com']
        })

        pii_fields = ["foo", "baa"]
        obfuscated_df = obfuscate(pii_fields, df.copy())

        assert all(obfuscated_df['name'] == df['name'])
        assert all(obfuscated_df['email'] == df['email'])
        assert all(obfuscated_df['age'] == df['age'])
        assert 'foo' not in obfuscated_df.columns
        assert 'bar' not in obfuscated_df.columns
