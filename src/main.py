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
        raise ValueError
    if not is_valid_s3_uri(config['file_to_obfuscate']):
        raise ValueError("Invalid S3 URI")
    return True

def load_df(s3_uri: str):
    parsed = urlparse(s3_uri)
    bucket = parsed.netloc           
    key = parsed.path.lstrip('/')    
    s3 = boto3.client('s3')
    print(bucket)
    response = s3.get_object(Bucket=bucket, Key=key)
    df = pd.read_csv(response['Body'])
    return df

def obfuscate(pii_fields, df):
    fields = pii_fields
    for field in fields:
        df[field] = '*****'
    return df

def upload(df, s3_uri):
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    s3 = boto3.client('s3')
    parsed = urlparse(s3_uri)
    bucket = parsed.netloc           
    key = parsed.path.lstrip('/')    
    s3.put_object(Bucket=bucket, Key=key, Body=csv_buffer.getvalue())    

    
def main():
    parser = argparse.ArgumentParser(description="Obfuscate PII fields in a file using JSON config")
    parser.add_argument('config', help="Path to JSON config file")
    args = parser.parse_args()

    with open(args.config, 'r') as f:
        config = json.load(f)

    df = load_df(config["file_to_obfuscate"])
    upload(obfuscate(config["pii_fields"], df), config["file_to_obfuscate"])

    
if __name__ == '__main__':
    main()
