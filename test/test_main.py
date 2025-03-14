import io
import json
import logging
import sys
import pytest
import pandas as pd
import boto3
from moto import mock_aws
from botocore.exceptions import ClientError
from typeguard import TypeCheckError
from src.main import (
    is_valid_s3_uri_and_file_type,
    json_checker,
    parse_s3_uri,
    load_config_from_json,
    load_df,
    obfuscate,
    get_csv_bytes,
)


class TestIsValidS3Uri:
    def test_valid_uri(self):
        uri = "s3://bucket/path/file.csv"
        assert is_valid_s3_uri_and_file_type(uri) is True

    def test_invalid_scheme(self):
        uri = "http://bucket/path/file.csv"
        assert is_valid_s3_uri_and_file_type(uri) is False
    
    def test_invalid_filetype(self):
        uri = "http://bucket/path/file.html"
        assert is_valid_s3_uri_and_file_type(uri) is False

    def test_missing_path(self):
        uri = "s3://bucket/"
        assert is_valid_s3_uri_and_file_type(uri) is False

class TestParseS3Uri:
    def test_parse(self):
        bucket, key = parse_s3_uri("s3://mybucket/mykey")
        assert bucket == "mybucket"
        assert key == "mykey"

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

class TestLoadConfigFromJson:
    def test_load_config_from_json(self, monkeypatch):
        test_json = '{"file_to_obfuscate": "s3://bucket/path/file.csv", "pii_fields": ["name", "email_address"]}'
        test_args = ['main.py', test_json]
        monkeypatch.setattr(sys, 'argv', test_args)
        expected = json.loads(test_json)
        config = load_config_from_json()
        assert config == expected


# Helper to generate a large CSV string.
def generate_large_csv(size_mb=1):
    target_size = size_mb * 1024 * 1024  
    csv_data = "col1,col2,col3\n"
    i = 0
    while len(csv_data.encode('utf-8')) < target_size:
        csv_data += f"{i},text{i},data{i}\n"
        i += 1
    return csv_data


# --- S3-dependent tests reimplemented with moto ---
class TestLoadDf:
    @mock_aws
    def test_load_df_success(self):
        s3 = boto3.client("s3", region_name="us-east-1")
        bucket = "mybucket"
        key = "mykey"
        s3.create_bucket(Bucket=bucket)
        csv_content = "col1,col2\n1,2\n3,4"
        s3.put_object(Bucket=bucket, Key=key, Body=csv_content)
        df = load_df(s3, f"s3://{bucket}/{key}")
        assert list(df.columns) == ['col1', 'col2']
        assert df.shape == (2, 2)

    @mock_aws
    def test_load_df_no_such_bucket(self):
        s3 = boto3.client("s3", region_name="us-east-1")
        with pytest.raises(ValueError, match="Invalid bucket: bucket does not exist"):
            load_df(s3, "s3://nonexistentbucket/mykey")

    @mock_aws
    def test_load_df_no_such_key(self):
        s3 = boto3.client("s3", region_name="us-east-1")
        bucket = "mybucket"
        s3.create_bucket(Bucket=bucket)
        with pytest.raises(ValueError, match="Invalid key: key does not exist"):
            load_df(s3, f"s3://{bucket}/nonexistentkey")


class TestPerformance:
    @mock_aws
    def test_large_file_speed(self, benchmark):
        s3 = boto3.client("s3", region_name="us-east-1")
        bucket = "bucket"
        key = "large.csv"
        s3.create_bucket(Bucket=bucket)
        csv_content = generate_large_csv()
        s3.put_object(Bucket=bucket, Key=key, Body=csv_content)
        
        def process():
            df = load_df(s3, f"s3://{bucket}/{key}")
            obfuscated = obfuscate(["col2"], df)
            return get_csv_bytes(obfuscated)
        
        result = benchmark(process)
        assert result is not None
        assert benchmark.stats.stats.total < 60 