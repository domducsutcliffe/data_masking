import argparse
import boto3
import io
import json
import pandas as pd
from typeguard import typechecked
from urllib.parse import urlparse

def is_valid_s3_uri(uri: str) -> bool:
    return bool((parsed := urlparse(uri)).scheme == 's3' 
                and parsed.netloc 
                and parsed.path 
                and parsed.path.endswith('.csv'))

@typechecked
def json_checker(obfuscation_config: str) -> bool:
    try:
        config = json.loads(obfuscation_config)
    except json.JSONDecodeError:
        raise
    keys = list(config.keys())
    if not keys[0] == 'file_to_obfuscate' or not keys[1] == 'pii_fields':
        raise ValueError("JSON keys are invalid.")
    if not is_valid_s3_uri(config['file_to_obfuscate']):
        raise ValueError("Invalid S3 URI")
    return True

def load_df(s3_uri: str):
    bucket, key = parse_s3_uri(s3_uri)    
    s3 = boto3.client('s3')
    response = s3.get_object(Bucket=bucket, Key=key)
    df = pd.read_csv(response['Body'])
    return df

def parse_s3_uri(s3_uri):
    parsed = urlparse(s3_uri)
    bucket = parsed.netloc           
    key = parsed.path.lstrip('/')
    return bucket,key

def obfuscate(pii_fields, df):
    for field in pii_fields:
        df[field] = '*****'
    return df

def upload(df, s3_uri: str):
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    bucket, key = parse_s3_uri(s3_uri)    
    s3 = boto3.client('s3')
    s3.put_object(Bucket=bucket, Key=key, Body=csv_buffer.getvalue())    

def load_config_from_json():
    parser = argparse.ArgumentParser(
        description="Obfuscate PII fields in a file using JSON config"
    )
    parser.add_argument(
        'config', 
        help='JSON config string in the format: {"file_to_obfuscate": "s3://your_bucket/path/file.csv", "pii_fields": ["name", "email_address"]}'
    )
    args = parser.parse_args()
    config = json.loads(args.config)
    return config

def main():
    config = load_config_from_json()
    json_checker(json.dumps(config))
    
    df = load_df(config["file_to_obfuscate"])
    obfuscated_df = obfuscate(config["pii_fields"], df)
    upload(obfuscated_df, config["file_to_obfuscate"])

if __name__ == '__main__':
    main()