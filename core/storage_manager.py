import boto3
import os
import pandas as pd
from botocore.exceptions import ClientError
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)

class StorageManager:
    """
    Handles Cold Storage (MinIO/S3) operations for long-term data archival.
    Optimized for multi-tenant Parquet storage.
    """
    def __init__(self):
        self.endpoint = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
        self.access_key = os.getenv("MINIO_ACCESS_KEY", "admin")
        self.secret_key = os.getenv("MINIO_SECRET_KEY", "password123")
        self.bucket_name = "sql-intel-archive"
        
        self.s3 = boto3.client(
            's3',
            endpoint_url=self.endpoint,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name='us-east-1'
        )
        self._ensure_bucket()

    def _ensure_bucket(self):
        try:
            self.s3.head_bucket(Bucket=self.bucket_name)
        except ClientError:
            self.s3.create_bucket(Bucket=self.bucket_name)
            logger.info("bucket_created", bucket=self.bucket_name)

    def archive_to_parquet(self, tenant_id: str, data: list, prefix: str):
        """
        Converts a list of dicts to Parquet and uploads to the tenant's cold zone.
        Path: {bucket}/{tenant_id}/{prefix}/{year}/{month}/{timestamp}.parquet
        """
        if not data:
            return None

        df = pd.DataFrame(data)
        
        # Schema normalization for Parquet (UUIDs to strings)
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].apply(lambda x: str(x) if x is not None else None)

        now = datetime.utcnow()
        file_name = f"{now.strftime('%Y%m%d_%H%M%S')}.parquet"
        local_path = f"/tmp/{file_name}"
        
        # Export to Parquet with compression
        df.to_parquet(local_path, compression='snappy', index=False)
        
        # S3 Path
        s3_key = f"{tenant_id}/{prefix}/{now.year}/{now.month}/{file_name}"
        
        try:
            self.s3.upload_file(local_path, self.bucket_name, s3_key)
            logger.info("archival_complete", tenant=tenant_id, key=s3_key, count=len(data))
            return s3_key
        finally:
            if os.path.exists(local_path):
                os.remove(local_path)

    def list_archives(self, tenant_id: str, prefix: str):
        """Lists historical cold storage files for a tenant."""
        prefix_path = f"{tenant_id}/{prefix}/"
        response = self.s3.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix_path)
        return [obj['Key'] for obj in response.get('Contents', [])]
