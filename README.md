# GDPR Obfuscator

A Python library for anonymising PII in CSV files stored in AWS S3. Designed for GDPR compliance in bulk data analysis workflows.

## Features
- Processes CSV files from S3, replacing specified PII fields with obfuscated strings.
- Returns a byte-stream compatible with boto3’s `PutObject`.
- Tested for security vulnerabilities and PEP-8 compliant.
- Handles files up to 1MB in under a minute.

## Usage
Provide a JSON string with:
```json
{
  "file_to_obfuscate": "s3://your_bucket/path/file.csv",
  "pii_fields": ["name", "email_address"]
}
```
The tool returns an obfuscated CSV byte-stream (e.g. with `name` and `email_address` replaced by `***`).

## Example
Original CSV:
```
student_id,name,email_address
1234,John Smith,j.smith@email.com
```
Obfuscated CSV:
```
student_id,name,email_address
1234,***,***
```

## Extensions
- JSON and Parquet support.
- Same output format as input.

## Prerequisites
- Python 3.x
- AWS SDK for Python (boto3)

## Performance
- Targeted file size: up to 1MB
- Runtime: under 1 minute

## Deployment
- Suitable for Lambda, ECS, EC2, or other AWS services. 
- No credentials stored in code. 
- Unit tested with standard Python testing frameworks.

## Due Date
Within four weeks of project start.