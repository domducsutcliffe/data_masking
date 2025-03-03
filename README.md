# GDPR Obfuscator

A command-line tool for anonymising PII in CSV files stored on AWS S3.

## Overview

The tool loads a CSV from an S3 URI provided via a JSON configuration string, replaces designated PII columns with `"***"`, and outputs the modified CSV. It uses robust validation, logging, and error handling to ensure correct processing.

## Installation

- Python 3.x  
- Install dependencies via pip:
  ```bash
  pip install -r requirements.txt
  ```

## Usage

Pass a JSON config as a command-line argument:
```bash
python main.py '{"file_to_obfuscate": "s3://your_bucket/path/file.csv", "pii_fields": ["name", "email_address"]}'
```
The program validates the JSON, downloads the CSV from S3, obfuscates the specified fields, and prints the obfuscated CSV as a UTF-8 string.

## Testing

Tests are implemented using pytest and moto for mocking AWS S3:
- To run tests:
  ```bash
  pytest
  ```

Tests cover:
- S3 URI parsing and validation.
- JSON configuration checks.
- Field obfuscation with logging warnings for missing columns.
- CSV conversion and performance benchmarks.

## Notes

- The tool assumes AWS credentials are provided externally.
- Designed for files up to 1MB, processing in under one minute.
- Logging is configured at INFO level for operational transparency.