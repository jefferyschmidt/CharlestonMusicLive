"""
Test the R2 client for Cloudflare R2 and local S3 storage.
"""
import pytest
import tempfile
import os
from io import BytesIO
from unittest.mock import patch, MagicMock
from storage.r2_client import R2Client, LocalS3Client


class TestLocalS3Client:
    """Test the local S3 client for development/testing."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.client = LocalS3Client(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_upload_artifact(self):
        """Test uploading an artifact to local storage."""
        key = "test/event_123.html"
        data = BytesIO(b"<html>Test content</html>")
        metadata = {"source": "test", "venue": "test_venue"}
        
        result = self.client.upload_artifact(key, data, content_type="text/html", metadata=metadata)
        
        assert result is True
        
        # Check file was created
        file_path = os.path.join(self.temp_dir, key)
        assert os.path.exists(file_path)
        
        # Check content
        with open(file_path, 'rb') as f:
            content = f.read()
        assert content == b"<html>Test content</html>"
        
        # Check metadata file
        meta_path = file_path + '.meta'
        assert os.path.exists(meta_path)
        
        with open(meta_path, 'r') as f:
            meta_content = f.read()
        assert "source: test" in meta_content
        assert "venue: test_venue" in meta_content
    
    def test_download_artifact(self):
        """Test downloading an artifact from local storage."""
        # Create test file
        key = "test/event_123.html"
        file_path = os.path.join(self.temp_dir, key)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'wb') as f:
            f.write(b"<html>Test content</html>")
        
        # Download artifact
        result = self.client.download_artifact(key)
        
        assert result is not None
        content = result.read()
        assert content == b"<html>Test content</html>"
        result.close()
    
    def test_download_nonexistent_artifact(self):
        """Test downloading a non-existent artifact."""
        result = self.client.download_artifact("nonexistent/file.html")
        assert result is None
    
    def test_delete_artifact(self):
        """Test deleting an artifact from local storage."""
        # Create test file and metadata
        key = "test/event_123.html"
        file_path = os.path.join(self.temp_dir, key)
        meta_path = file_path + '.meta'
        
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'wb') as f:
            f.write(b"<html>Test content</html>")
        
        with open(meta_path, 'w') as f:
            f.write("source: test\n")
        
        # Delete artifact
        result = self.client.delete_artifact(key)
        
        assert result is True
        assert not os.path.exists(file_path)
        assert not os.path.exists(meta_path)
    
    def test_delete_nonexistent_artifact(self):
        """Test deleting a non-existent artifact."""
        result = self.client.delete_artifact("nonexistent/file.html")
        assert result is False
    
    def test_list_artifacts(self):
        """Test listing artifacts in local storage."""
        # Create test files
        test_files = [
            "test/event_1.html",
            "test/event_2.html",
            "other/event_3.html"
        ]
        
        for file_path in test_files:
            full_path = os.path.join(self.temp_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'wb') as f:
                f.write(b"test content")
        
        # List all artifacts
        artifacts = self.client.list_artifacts()
        assert len(artifacts) == 3
        assert "test/event_1.html" in artifacts
        assert "test/event_2.html" in artifacts
        assert "other/event_3.html" in artifacts
        
        # List artifacts with prefix
        test_artifacts = self.client.list_artifacts(prefix="test/")
        assert len(test_artifacts) == 2
        assert "test/event_1.html" in test_artifacts
        assert "test/event_2.html" in test_artifacts
    
    def test_artifact_exists(self):
        """Test checking if artifact exists."""
        # Create test file
        key = "test/event_123.html"
        file_path = os.path.join(self.temp_dir, key)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'wb') as f:
            f.write(b"test content")
        
        # Check existence
        assert self.client.artifact_exists(key) is True
        assert self.client.artifact_exists("nonexistent/file.html") is False
    
    def test_get_artifact_metadata(self):
        """Test getting artifact metadata."""
        # Create test file and metadata
        key = "test/event_123.html"
        file_path = os.path.join(self.temp_dir, key)
        meta_path = file_path + '.meta'
        
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'wb') as f:
            f.write(b"<html>Test content</html>")
        
        with open(meta_path, 'w') as f:
            f.write("source: test\nvenue: test_venue\n")
        
        # Get metadata
        metadata = self.client.get_artifact_metadata(key)
        
        assert metadata is not None
        assert metadata['content_length'] == 25  # Length of b"<html>Test content</html>"
        assert 'last_modified' in metadata
        assert metadata['metadata']['source'] == 'test'
        assert metadata['metadata']['venue'] == 'test_venue'
    
    def test_get_nonexistent_artifact_metadata(self):
        """Test getting metadata for non-existent artifact."""
        metadata = self.client.get_artifact_metadata("nonexistent/file.html")
        assert metadata is None


class TestR2Client:
    """Test the R2 client for Cloudflare R2."""
    
    @patch('storage.r2_client.boto3.client')
    @patch('storage.r2_client.boto3.resource')
    def test_init_success(self, mock_resource, mock_client):
        """Test successful R2 client initialization."""
        mock_client.return_value = MagicMock()
        mock_resource.return_value = MagicMock()
        
        client = R2Client(
            account_id="test_account",
            access_key_id="test_key",
            secret_access_key="test_secret",
            bucket_name="test_bucket"
        )
        
        assert client.account_id == "test_account"
        assert client.access_key_id == "test_key"
        assert client.secret_access_key == "test_secret"
        assert client.bucket_name == "test_bucket"
        
        mock_client.assert_called_once()
        mock_resource.assert_called_once()
    
    def test_init_missing_credentials(self):
        """Test R2 client initialization with missing credentials."""
        with pytest.raises(ValueError, match="Missing required R2 configuration"):
            R2Client()
    
    @patch('storage.r2_client.boto3.client')
    @patch('storage.r2_client.boto3.resource')
    def test_upload_artifact_success(self, mock_resource, mock_client):
        """Test successful artifact upload."""
        mock_s3_client = MagicMock()
        mock_client.return_value = mock_s3_client
        mock_resource.return_value = MagicMock()
        
        client = R2Client(
            account_id="test_account",
            access_key_id="test_key",
            secret_access_key="test_secret",
            bucket_name="test_bucket"
        )
        
        data = BytesIO(b"test content")
        result = client.upload_artifact("test/key.txt", data, content_type="text/plain")
        
        assert result is True
        mock_s3_client.upload_fileobj.assert_called_once()
    
    @patch('storage.r2_client.boto3.client')
    @patch('storage.r2_client.boto3.resource')
    def test_upload_artifact_failure(self, mock_resource, mock_client):
        """Test failed artifact upload."""
        from botocore.exceptions import ClientError
        
        mock_s3_client = MagicMock()
        mock_s3_client.upload_fileobj.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access Denied'}},
            'UploadFileobj'
        )
        mock_client.return_value = mock_s3_client
        mock_resource.return_value = MagicMock()
        
        client = R2Client(
            account_id="test_account",
            access_key_id="test_key",
            secret_access_key="test_secret",
            bucket_name="test_bucket"
        )
        
        data = BytesIO(b"test content")
        result = client.upload_artifact("test/key.txt", data)
        
        assert result is False
    
    @patch('storage.r2_client.boto3.client')
    @patch('storage.r2_client.boto3.resource')
    def test_download_artifact_success(self, mock_resource, mock_client):
        """Test successful artifact download."""
        mock_s3_client = MagicMock()
        mock_response = MagicMock()
        mock_body = BytesIO(b"test content")
        mock_response.__getitem__.side_effect = lambda x: mock_body if x == 'Body' else None
        mock_s3_client.get_object.return_value = mock_response
        mock_client.return_value = mock_s3_client
        mock_resource.return_value = MagicMock()
        
        client = R2Client(
            account_id="test_account",
            access_key_id="test_key",
            secret_access_key="test_secret",
            bucket_name="test_bucket"
        )
        
        result = client.download_artifact("test/key.txt")
        
        assert result is not None
        content = result.read()
        assert content == b"test content"
    
    @patch('storage.r2_client.boto3.client')
    @patch('storage.r2_client.boto3.resource')
    def test_download_nonexistent_artifact(self, mock_resource, mock_client):
        """Test downloading non-existent artifact."""
        from botocore.exceptions import ClientError
        
        mock_s3_client = MagicMock()
        mock_s3_client.get_object.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchKey', 'Message': 'Not Found'}},
            'GetObject'
        )
        mock_client.return_value = mock_s3_client
        mock_resource.return_value = MagicMock()
        
        client = R2Client(
            account_id="test_account",
            access_key_id="test_key",
            secret_access_key="test_secret",
            bucket_name="test_bucket"
        )
        
        result = client.download_artifact("test/key.txt")
        
        assert result is None
    
    @patch('storage.r2_client.boto3.client')
    @patch('storage.r2_client.boto3.resource')
    def test_list_artifacts_success(self, mock_resource, mock_client):
        """Test successful artifact listing."""
        mock_s3_client = MagicMock()
        
        # Mock the list_objects_v2 method to return different results based on prefix
        def mock_list_objects_v2(**kwargs):
            if kwargs.get('Prefix') == 'test/':
                return {
                    'Contents': [
                        {'Key': 'test/file1.txt'},
                        {'Key': 'test/file2.txt'}
                    ]
                }
            else:
                return {
                    'Contents': [
                        {'Key': 'test/file1.txt'},
                        {'Key': 'test/file2.txt'},
                        {'Key': 'other/file3.txt'}
                    ]
                }
        
        mock_s3_client.list_objects_v2.side_effect = mock_list_objects_v2
        mock_client.return_value = mock_s3_client
        mock_resource.return_value = MagicMock()
        
        client = R2Client(
            account_id="test_account",
            access_key_id="test_key",
            secret_access_key="test_secret",
            bucket_name="test_bucket"
        )
        
        # Test with prefix
        artifacts = client.list_artifacts(prefix="test/")
        assert len(artifacts) == 2
        assert "test/file1.txt" in artifacts
        assert "test/file2.txt" in artifacts
        assert "other/file3.txt" not in artifacts
        
        # Test without prefix
        all_artifacts = client.list_artifacts()
        assert len(all_artifacts) == 3
        assert "test/file1.txt" in all_artifacts
        assert "test/file2.txt" in all_artifacts
        assert "other/file3.txt" in all_artifacts
