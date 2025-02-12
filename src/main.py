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

def load_csv():
    s3 = boto3.client('s3')
    response = s3.get_object(Bucket='csv-test-11022025', Key='file.csv')
    df = pd.read_csv(response['Body'])
    return df

def main():
    df = load_csv()
    df['name'] = '*****'
    print(df.head())
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    s3 = boto3.client('s3')
    s3.put_object(Bucket='csv-test-11022025', Key='file.csv', Body=csv_buffer.getvalue())    

if __name__ == '__main__':
    main()
