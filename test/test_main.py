import io
import json
import logging
import sys
import pytest
import pandas as pd
from botocore.exceptions import ClientError
from typeguard import TypeCheckError
from src.main import (
    is_valid_s3_uri,
    json_checker,
    parse_s3_uri,
    load_config_from_json,
    load_df,
    obfuscate,
    get_csv_bytes,
)

# Helper class to simulate S3 behaviour.
class FakeS3:
    def __init__(self, behaviour):
        self.behaviour = behaviour

    def get_object(self, Bucket, Key):
        if 'error' in self.behaviour:
            error_code = self.behaviour['error']
            raise ClientError({'Error': {'Code': error_code}}, 'get_object')
        csv_content = self.behaviour.get('csv_content', "col1,col2\n1,2\n3,4")
        return {'Body': io.StringIO(csv_content)}

# Tests for is_valid_s3_uri.
class TestIsValidS3Uri:
    def test_valid_uri(self):
        uri = "s3://bucket/path/file.csv"
        assert is_valid_s3_uri(uri) is True

    def test_invalid_scheme(self):
        uri = "http://bucket/path/file.csv"
        assert is_valid_s3_uri(uri) is False
    
    def test_invalid_filetype(self):
        uri = "http://bucket/path/file.html"
        assert is_valid_s3_uri(uri) is False

    def test_missing_path(self):
        uri = "s3://bucket/"
        assert is_valid_s3_uri(uri) is False

# Tests for parse_s3_uri.
class TestParseS3Uri:
    def test_parse(self):
        bucket, key = parse_s3_uri("s3://mybucket/mykey")
        assert bucket == "mybucket"
        assert key == "mykey"

# Tests for json_checker.
class TestJSONChecker:
    def test_no_args(self):
        with pytest.raises(TypeError):
            json_checker()

    @pytest.mark.parametrize("bad_arg", [
        [1, 2, 3],
        (1, 2, 3),
        42,
    ])
    def test_bad_data_type(self, bad_arg):
        with pytest.raises(TypeCheckError):
            json_checker(bad_arg)

    def test_valid_json(self):
        valid = '{"file_to_obfuscate": "s3://bucket/path/file.csv", "pii_fields": ["name", "email"]}'
        assert json_checker(valid)

    def test_malformed_json(self):
        malformed = '{"file_to_obfuscate": "s3://bucket/path/file.csv", "pii_fields": ["name", "email"]'
        with pytest.raises(json.JSONDecodeError):
            json_checker(malformed)

    def test_incorrect_json_keys(self):
        malformed = '{"foo": "s3://bucket/path/file.csv", "bar": ["name", "email"]}'
        with pytest.raises(ValueError):
            json_checker(malformed)

    def test_invalid_s3_uri_in_json(self):
        bad_uri = '{"file_to_obfuscate": "https://bucket/path/file.csv", "pii_fields": ["name", "email"]}'
        with pytest.raises(ValueError):
            json_checker(bad_uri)

# Tests for obfuscate.
class TestObfuscate:
    def test_no_pii_fields(self):
        df = pd.DataFrame({
            'name': ['Alice', 'Bob'],
            'age': [25, 30],
            'email': ['alice@example.com', 'bob@example.com']
        })
        result = obfuscate([], df.copy())
        pd.testing.assert_frame_equal(result, df)

    def test_two_pii_fields(self):
        df = pd.DataFrame({
            'name': ['Alice', 'Bob'],
            'age': [25, 30],
            'email': ['alice@example.com', 'bob@example.com']
        })
        result = obfuscate(['name', 'email'], df.copy())
        assert all(result['name'] == '***')
        assert all(result['email'] == '***')
        pd.testing.assert_series_equal(result['age'], df['age'])

    def test_invalid_pii_fields_logs_warning(self, caplog):
        df = pd.DataFrame({
            'name': ['Alice', 'Bob'],
            'age': [25, 30],
            'email': ['alice@example.com', 'bob@example.com']
        })
        with caplog.at_level(logging.WARNING):
            result = obfuscate(["foo", "bar"], df.copy())
        warnings = [record.message for record in caplog.records]
        pd.testing.assert_frame_equal(result, df)
        assert 'Field "foo" not provided' in warnings
        assert 'Field "bar" not provided' in warnings

# Tests for get_csv_bytes.
class TestGetCsvBytes:
    def test_get_csv_bytes(self):
        df = pd.DataFrame({
            'col1': [1, 2],
            'col2': [3, 4]
        })
        csv_bytes = get_csv_bytes(df)
        csv_str = csv_bytes.decode('utf-8')
        assert "col1,col2" in csv_str
        lines = csv_str.strip().split('\n')
        assert len(lines) == 3  
# Tests for load_df.
class TestLoadDf:
    def test_success(self):
        fake_s3 = FakeS3({'csv_content': "col1,col2\n1,2\n3,4"})
        df = load_df(fake_s3, "s3://mybucket/mykey")
        assert list(df.columns) == ['col1', 'col2']
        assert df.shape == (2, 2)

    def test_no_such_bucket(self):
        fake_s3 = FakeS3({'error': 'NoSuchBucket'})
        with pytest.raises(ValueError, match="Invalid bucket: bucket does not exist"):
            load_df(fake_s3, "s3://nonexistentbucket/mykey")

    def test_no_such_key(self):
        fake_s3 = FakeS3({'error': 'NoSuchKey'})
        with pytest.raises(ValueError, match="Invalid key: key does not exist"):
            load_df(fake_s3, "s3://mybucket/nonexistentkey")

    def test_generic_client_error(self):
        fake_s3 = FakeS3({'error': 'SomeOtherError'})
        with pytest.raises(ValueError, match="Failed to retrieve object: SomeOtherError"):
            load_df(fake_s3, "s3://mybucket/mykey")


# Tests for load_config_from_json.
class TestLoadConfigFromJson:
    def test_load_config_from_json(self, monkeypatch):
        test_json = '{"file_to_obfuscate": "s3://bucket/path/file.csv", "pii_fields": ["name", "email_address"]}'
        test_args = ['program', test_json]
        monkeypatch.setattr(sys, 'argv', test_args)
        expected = json.loads(test_json)
        config = load_config_from_json()
        assert config == expected