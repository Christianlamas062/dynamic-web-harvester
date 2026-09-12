import json
import logging
import os
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class S3DataSink:

    def __init__(
        self,
        bucket_name: str | None = None,
        region: str | None = None,
    ):
        self.bucket_name = bucket_name or os.getenv("S3_BUCKET_NAME", "harvester-data-christian-2026")
        region_name = region or os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        self.s3_client = boto3.client("s3", region_name=region_name)

    def upload_raw_payload(self, data: list | dict, prefix: str = "raw"):
        timestamp = datetime.utcnow().strftime("%Y/%m/%d/%H%M%S")
        object_key = f"{prefix}/{timestamp}_records.json"

        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=object_key,
                Body=json.dumps(data, indent=2, default=str),
                ContentType="application/json",
            )
            logger.info(
                f"Payload guardado en s3://{self.bucket_name}/{object_key}"
            )
            return object_key
        except ClientError as e:
            logger.error(f"Fallo al subir a S3: {e}")
            raise
