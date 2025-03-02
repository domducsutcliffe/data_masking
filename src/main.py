import argparse
import boto3
from botocore.exceptions import ClientError
import io
import json
import logging
import pandas as pd
from typeguard import typechecked
from urllib.parse import urlparse


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_config_from_json() -> dict:
    parser = argparse.ArgumentParser(
        description="Obfuscate PII fields in a file using JSON config"
    )
    parser.add_argument(
        'config', 
        help='JSON config string in the format: {"file_to_obfuscate": "s3://your_bucket/path/file.csv", "pii_fields": ["name", "email_address"]}'
    )
    args = parser.parse_args()
    return json.loads(args.config)

@typechecked
def json_checker(obfuscation_config: str) -> bool:
    try:
        config = json.loads(obfuscation_config)
    except json.JSONDecodeError:
        raise
    keys = list(config.keys())
    if not keys[0] == 'file_to_obfuscate' or not keys[1] == 'pii_fields':
        raise ValueError("JSON keys are invalid.")
    if not is_valid_s3_uri_and_file_type(config['file_to_obfuscate']):
        raise ValueError("Invalid S3 URI")
    return True

def is_valid_s3_uri_and_file_type(uri: str) -> bool:
    return bool((parsed := urlparse(uri)).scheme == 's3' 
                and parsed.netloc 
                and parsed.path 
                and parsed.path.endswith('.csv'))



def load_df(s3, s3_uri: str) -> pd.DataFrame:
    bucket, key = parse_s3_uri(s3_uri)
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        if error_code == "NoSuchBucket":
            raise ValueError("Invalid bucket: bucket does not exist") from e
        elif error_code == "NoSuchKey":
            raise ValueError("Invalid key: key does not exist") from e
        raise ValueError(f"Failed to retrieve object: {error_code}") from e
    try:
        return pd.read_csv(response['Body'])
    except Exception as e:
        raise ValueError("Failed to parse CSV from S3 object") from e

def parse_s3_uri(s3_uri: str) -> tuple[str, str]:
    parsed = urlparse(s3_uri)
    bucket = parsed.netloc           
    key = parsed.path.lstrip('/')
    return bucket, key

def obfuscate(pii_fields, df: pd.DataFrame) -> pd.DataFrame:
    fields_obfuscated = 0
    record_count = len(df)
    for field in pii_fields:
        if field in df.columns:
            fields_obfuscated += 1
            df[field] = "***"
        else:
            logger.warning(f'Field "{field}" not provided')
    logger.info(f'{fields_obfuscated} fields obfuscated in {record_count} records')
    return df

def get_csv_bytes(df: pd.DataFrame) -> bytes:
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    return csv_buffer.getvalue().encode('utf-8')


def main():
    config = load_config_from_json()
    json_checker(json.dumps(config))
    s3 = boto3.client('s3')
    df = load_df(s3, config["file_to_obfuscate"])    
    obfuscated_df = obfuscate(config["pii_fields"], df)
    csv_bytes = get_csv_bytes(obfuscated_df)
    print(csv_bytes.decode('utf-8'))

if __name__ == '__main__':
    main()