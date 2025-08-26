"""
Cloudflare R2 (S3-compatible) client for raw artifact storage.
"""
import os
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Optional, Dict, Any, BinaryIO
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class R2Client:
    """Client for Cloudflare R2 object storage."""
    
    def __init__(
        self,
        account_id: Optional[str] = None,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        bucket_name: Optional[str] = None,
        region: str = "auto"
    ):
        """Initialize R2 client.
        
        Args:
            account_id: Cloudflare account ID
            access_key_id: R2 access key ID
            secret_access_key: R2 secret access key
            bucket_name: R2 bucket name
            region: R2 region (usually "auto")
        """
        self.account_id = account_id or os.getenv("R2_ACCOUNT_ID")
        self.access_key_id = access_key_id or os.getenv("R2_ACCESS_KEY_ID")
        self.secret_access_key = secret_access_key or os.getenv("R2_SECRET_ACCESS_KEY")
        self.bucket_name = bucket_name or os.getenv("R2_BUCKET_NAME")
        self.region = region
        
        if not all([self.account_id, self.access_key_id, self.secret_access_key, self.bucket_name]):
            raise ValueError("Missing required R2 configuration. Set environment variables or pass parameters.")
        
        # Initialize S3 client for R2
        self.s3_client = boto3.client(
            's3',
            endpoint_url=f"https://{self.account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            region_name=self.region
        )
        
        # Initialize S3 resource for higher-level operations
        self.s3_resource = boto3.resource(
            's3',
            endpoint_url=f"https://{self.account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            region_name=self.region
        )
    
    def upload_artifact(
        self,
        key: str,
        data: BinaryIO,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> bool:
        """Upload a raw artifact to R2.
        
        Args:
            key: Object key (path) in the bucket
            data: File-like object to upload
            content_type: MIME type of the content
            metadata: Additional metadata to store
            
        Returns:
            True if upload successful, False otherwise
        """
        try:
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
            if metadata:
                extra_args['Metadata'] = metadata
            
            self.s3_client.upload_fileobj(
                data,
                self.bucket_name,
                key,
                ExtraArgs=extra_args
            )
            
            logger.info(f"Successfully uploaded artifact: {key}")
            return True
            
        except (ClientError, NoCredentialsError) as e:
            logger.error(f"Failed to upload artifact {key}: {e}")
            return False
    
    def download_artifact(self, key: str) -> Optional[BinaryIO]:
        """Download a raw artifact from R2.
        
        Args:
            key: Object key (path) in the bucket
            
        Returns:
            File-like object if successful, None otherwise
        """
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            return response['Body']
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.warning(f"Artifact not found: {key}")
            else:
                logger.error(f"Failed to download artifact {key}: {e}")
            return None
    
    def delete_artifact(self, key: str) -> bool:
        """Delete a raw artifact from R2.
        
        Args:
            key: Object key (path) in the bucket
            
        Returns:
            True if deletion successful, False otherwise
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            logger.info(f"Successfully deleted artifact: {key}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to delete artifact {key}: {e}")
            return False
    
    def list_artifacts(
        self,
        prefix: Optional[str] = None,
        max_keys: int = 1000
    ) -> list:
        """List artifacts in the bucket.
        
        Args:
            prefix: Filter objects by key prefix
            max_keys: Maximum number of keys to return
            
        Returns:
            List of object keys
        """
        try:
            kwargs = {
                'Bucket': self.bucket_name,
                'MaxKeys': max_keys
            }
            if prefix:
                kwargs['Prefix'] = prefix
            
            response = self.s3_client.list_objects_v2(**kwargs)
            
            if 'Contents' in response:
                return [obj['Key'] for obj in response['Contents']]
            return []
            
        except ClientError as e:
            logger.error(f"Failed to list artifacts: {e}")
            return []
    
    def get_artifact_url(self, key: str, expires_in: int = 3600) -> Optional[str]:
        """Generate a presigned URL for downloading an artifact.
        
        Args:
            key: Object key (path) in the bucket
            expires_in: URL expiration time in seconds
            
        Returns:
            Presigned URL if successful, None otherwise
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': key},
                ExpiresIn=expires_in
            )
            return url
            
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL for {key}: {e}")
            return None
    
    def artifact_exists(self, key: str) -> bool:
        """Check if an artifact exists in the bucket.
        
        Args:
            key: Object key (path) in the bucket
            
        Returns:
            True if artifact exists, False otherwise
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            logger.error(f"Error checking artifact existence for {key}: {e}")
            return False
    
    def get_artifact_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """Get metadata for an artifact.
        
        Args:
            key: Object key (path) in the bucket
            
        Returns:
            Dictionary of metadata if successful, None otherwise
        """
        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            
            metadata = {
                'content_length': response.get('ContentLength'),
                'content_type': response.get('ContentType'),
                'last_modified': response.get('LastModified'),
                'etag': response.get('ETag'),
                'metadata': response.get('Metadata', {})
            }
            
            return metadata
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                logger.warning(f"Artifact not found: {key}")
            else:
                logger.error(f"Failed to get metadata for artifact {key}: {e}")
            return None
    
    def cleanup_old_artifacts(
        self,
        prefix: str,
        days_old: int = 30,
        dry_run: bool = True
    ) -> list:
        """Clean up old artifacts based on age.
        
        Args:
            prefix: Filter objects by key prefix
            days_old: Delete artifacts older than this many days
            dry_run: If True, only list what would be deleted
            
        Returns:
            List of deleted/listed object keys
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        artifacts_to_delete = []
        
        try:
            # List all artifacts with the given prefix
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            if 'Contents' not in response:
                return []
            
            for obj in response['Contents']:
                if obj['LastModified'] < cutoff_date:
                    artifacts_to_delete.append(obj['Key'])
            
            if not dry_run and artifacts_to_delete:
                # Delete old artifacts
                for key in artifacts_to_delete:
                    self.delete_artifact(key)
                logger.info(f"Deleted {len(artifacts_to_delete)} old artifacts")
            elif dry_run:
                logger.info(f"Would delete {len(artifacts_to_delete)} old artifacts")
            
            return artifacts_to_delete
            
        except ClientError as e:
            logger.error(f"Failed to cleanup old artifacts: {e}")
            return []


class LocalS3Client:
    """Local S3-compatible client for development/testing."""
    
    def __init__(self, local_path: str = "./local_storage"):
        """Initialize local S3 client.
        
        Args:
            local_path: Local directory to store files
        """
        self.local_path = local_path
        os.makedirs(local_path, exist_ok=True)
    
    def upload_artifact(
        self,
        key: str,
        data: BinaryIO,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> bool:
        """Upload artifact to local storage."""
        try:
            file_path = os.path.join(self.local_path, key)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'wb') as f:
                f.write(data.read())
            
            # Store metadata in a sidecar file
            if metadata:
                meta_path = file_path + '.meta'
                with open(meta_path, 'w') as f:
                    for k, v in metadata.items():
                        f.write(f"{k}: {v}\n")
            
            logger.info(f"Successfully uploaded artifact to local storage: {key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload artifact {key} to local storage: {e}")
            return False
    
    def download_artifact(self, key: str) -> Optional[BinaryIO]:
        """Download artifact from local storage."""
        try:
            file_path = os.path.join(self.local_path, key)
            if not os.path.exists(file_path):
                return None
            
            return open(file_path, 'rb')
            
        except Exception as e:
            logger.error(f"Failed to download artifact {key} from local storage: {e}")
            return None
    
    def delete_artifact(self, key: str) -> bool:
        """Delete artifact from local storage."""
        try:
            file_path = os.path.join(self.local_path, key)
            if os.path.exists(file_path):
                os.remove(file_path)
                
                # Also remove metadata file if it exists
                meta_path = file_path + '.meta'
                if os.path.exists(meta_path):
                    os.remove(meta_path)
                
                logger.info(f"Successfully deleted artifact from local storage: {key}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete artifact {key} from local storage: {e}")
            return False
    
    def list_artifacts(
        self,
        prefix: Optional[str] = None,
        max_keys: int = 1000
    ) -> list:
        """List artifacts in local storage."""
        try:
            artifacts = []
            for root, dirs, files in os.walk(self.local_path):
                for file in files:
                    if file.endswith('.meta'):
                        continue
                    
                    rel_path = os.path.relpath(os.path.join(root, file), self.local_path)
                    if not prefix or rel_path.startswith(prefix):
                        artifacts.append(rel_path)
                        
                        if len(artifacts) >= max_keys:
                            break
                
                if len(artifacts) >= max_keys:
                    break
            
            return artifacts
            
        except Exception as e:
            logger.error(f"Failed to list artifacts from local storage: {e}")
            return []
    
    def artifact_exists(self, key: str) -> bool:
        """Check if artifact exists in local storage."""
        file_path = os.path.join(self.local_path, key)
        return os.path.exists(file_path)
    
    def get_artifact_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """Get metadata for artifact in local storage."""
        try:
            file_path = os.path.join(self.local_path, key)
            if not os.path.exists(file_path):
                return None
            
            stat = os.stat(file_path)
            metadata = {
                'content_length': stat.st_size,
                'last_modified': datetime.fromtimestamp(stat.st_mtime),
                'metadata': {}
            }
            
            # Try to read metadata from sidecar file
            meta_path = file_path + '.meta'
            if os.path.exists(meta_path):
                with open(meta_path, 'r') as f:
                    for line in f:
                        if ':' in line:
                            k, v = line.strip().split(':', 1)
                            metadata['metadata'][k.strip()] = v.strip()
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to get metadata for artifact {key} from local storage: {e}")
            return None
