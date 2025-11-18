import pytest
import json
from unittest.mock import Mock, patch, MagicMock
import azure.functions as func
from function_app import AnaplanApiExport, upload_data_to_blob


class TestAnaplanApiExport:
    """Test suite for AnaplanApiExport Azure Function"""

    @pytest.fixture
    def valid_request_body(self):
        """Fixture for a valid request body with all required parameters"""
        return {
            'username': 'test_user',
            'password': 'test_pass',
            'account_name': 'testaccount',
            'account_key': 'testkey123',
            'container_name': 'testcontainer',
            'Anaplan_Auth_Url': 'https://auth.anaplan.com/token/authenticate',
            'AnaplanExportFile': 'export_data.csv',
            'workspace_id': 'workspace123',
            'model_id': 'model123',
            'export_id': 'export123',
            'api_url': 'https://api.anaplan.com/2/0/workspaces',
            'foldername': 'exports',
            'environment': 'test'
        }

    @pytest.fixture
    def mock_http_request(self, valid_request_body):
        """Fixture for a mock HTTP request"""
        req = Mock(spec=func.HttpRequest)
        req.get_json.return_value = valid_request_body
        return req

    def test_missing_required_parameters(self):
        """Test that missing parameters return HTTP 400"""
        # Create request with missing parameters
        req = Mock(spec=func.HttpRequest)
        req.get_json.return_value = {
            'username': 'test_user',
            'password': 'test_pass',
            # Missing all other required parameters
        }

        response = AnaplanApiExport(req)

        assert response.status_code == 400
        assert 'Missing required parameters' in response.get_body().decode()

    def test_invalid_json_request(self):
        """Test that invalid JSON returns HTTP 400"""
        req = Mock(spec=func.HttpRequest)
        req.get_json.side_effect = ValueError("Invalid JSON")

        response = AnaplanApiExport(req)

        assert response.status_code == 400
        assert 'Invalid JSON' in response.get_body().decode()

    def test_all_required_parameters_present(self, mock_http_request, valid_request_body):
        """Test that all required parameters are checked"""
        required_params = [
            'username', 'password', 'account_name', 'account_key', 'container_name',
            'Anaplan_Auth_Url', 'AnaplanExportFile', 'workspace_id', 'model_id',
            'export_id', 'api_url', 'foldername', 'environment'
        ]

        for param in required_params:
            # Test with one parameter missing at a time
            incomplete_body = valid_request_body.copy()
            del incomplete_body[param]

            req = Mock(spec=func.HttpRequest)
            req.get_json.return_value = incomplete_body

            response = AnaplanApiExport(req)

            assert response.status_code == 400
            assert param in response.get_body().decode(), f"Missing parameter {param} not detected"

    @patch('function_app.requests.post')
    def test_authentication_failure(self, mock_post, mock_http_request):
        """Test authentication failure handling"""
        # Mock failed authentication
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_post.return_value = mock_response

        response = AnaplanApiExport(mock_http_request)

        assert response.status_code == 500
        assert 'Failed to authenticate' in response.get_body().decode()

    @patch('function_app.upload_data_to_blob')
    @patch('function_app.requests.get')
    @patch('function_app.requests.post')
    def test_successful_export(self, mock_post, mock_get, mock_upload, mock_http_request):
        """Test successful export flow"""
        # Mock authentication
        auth_response = Mock()
        auth_response.status_code = 200
        auth_response.json.return_value = {
            'tokenInfo': {'tokenValue': 'test_token_123'}
        }

        # Mock export task creation
        task_response = Mock()
        task_response.status_code = 200
        task_response.json.return_value = {
            'task': {'taskId': 'task123'}
        }

        # Mock export definition
        export_def_response = Mock()
        export_def_response.status_code = 200
        export_def_response.json.return_value = {
            'exportMetadata': {'fileId': 'file123'}
        }

        # Mock task status (completed)
        task_status_response = Mock()
        task_status_response.status_code = 200
        task_status_response.json.return_value = {
            'task': {'taskState': 'COMPLETE'}
        }

        # Mock chunks response
        chunks_response = Mock()
        chunks_response.status_code = 200
        chunks_response.json.return_value = {
            'chunks': [{'id': 'chunk1'}, {'id': 'chunk2'}]
        }

        # Mock chunk data
        chunk_data_response = Mock()
        chunk_data_response.content = b"test,data\n1,2"

        # Setup mock responses in order
        mock_post.side_effect = [auth_response, task_response]
        mock_get.side_effect = [
            export_def_response,
            task_status_response,
            chunks_response,
            chunk_data_response,
            chunk_data_response
        ]

        response = AnaplanApiExport(mock_http_request)

        assert response.status_code == 200
        assert 'uploaded successfully' in response.get_body().decode()
        mock_upload.assert_called_once()

    @patch('function_app.requests.post')
    def test_export_definition_failure(self, mock_post, mock_http_request):
        """Test export definition retrieval failure"""
        # Mock successful authentication
        auth_response = Mock()
        auth_response.status_code = 200
        auth_response.json.return_value = {
            'tokenInfo': {'tokenValue': 'test_token'}
        }
        mock_post.return_value = auth_response

        # Mock failed export definition retrieval
        with patch('function_app.requests.get') as mock_get:
            export_def_response = Mock()
            export_def_response.status_code = 404
            export_def_response.text = "Not found"
            mock_get.return_value = export_def_response

            response = AnaplanApiExport(mock_http_request)

            assert response.status_code == 500
            assert 'Failed to get export definition' in response.get_body().decode()

    @patch('function_app.requests.get')
    @patch('function_app.requests.post')
    def test_export_task_failed(self, mock_post, mock_get, mock_http_request):
        """Test handling of failed export task"""
        # Mock authentication
        auth_response = Mock()
        auth_response.status_code = 200
        auth_response.json.return_value = {
            'tokenInfo': {'tokenValue': 'test_token'}
        }

        # Mock task creation
        task_response = Mock()
        task_response.status_code = 200
        task_response.json.return_value = {
            'task': {'taskId': 'task123'}
        }

        mock_post.side_effect = [auth_response, task_response]

        # Mock export definition
        export_def_response = Mock()
        export_def_response.status_code = 200
        export_def_response.json.return_value = {
            'exportMetadata': {'fileId': 'file123'}
        }

        # Mock task status (failed)
        task_status_response = Mock()
        task_status_response.status_code = 200
        task_status_response.json.return_value = {
            'task': {'taskState': 'FAILED'}
        }

        mock_get.side_effect = [export_def_response, task_status_response]

        response = AnaplanApiExport(mock_http_request)

        assert response.status_code == 500
        assert 'Export task failed' in response.get_body().decode()

    @patch('function_app.requests.get')
    @patch('function_app.requests.post')
    def test_no_chunks_found(self, mock_post, mock_get, mock_http_request):
        """Test handling when no chunks are found"""
        # Mock successful authentication and task completion
        auth_response = Mock()
        auth_response.status_code = 200
        auth_response.json.return_value = {
            'tokenInfo': {'tokenValue': 'test_token'}
        }

        task_response = Mock()
        task_response.status_code = 200
        task_response.json.return_value = {
            'task': {'taskId': 'task123'}
        }

        mock_post.side_effect = [auth_response, task_response]

        # Mock export definition and task status
        export_def_response = Mock()
        export_def_response.status_code = 200
        export_def_response.json.return_value = {
            'exportMetadata': {'fileId': 'file123'}
        }

        task_status_response = Mock()
        task_status_response.status_code = 200
        task_status_response.json.return_value = {
            'task': {'taskState': 'COMPLETE'}
        }

        # Mock empty chunks response
        chunks_response = Mock()
        chunks_response.status_code = 200
        chunks_response.json.return_value = {'chunks': []}

        mock_get.side_effect = [export_def_response, task_status_response, chunks_response]

        response = AnaplanApiExport(mock_http_request)

        assert response.status_code == 500
        assert 'No chunks found' in response.get_body().decode()

    @patch('function_app.requests.post')
    def test_missing_key_in_response(self, mock_post, mock_http_request):
        """Test handling of missing keys in API response"""
        # Mock authentication with missing key
        auth_response = Mock()
        auth_response.status_code = 200
        auth_response.json.return_value = {
            # Missing 'tokenInfo' key
            'wrongKey': 'value'
        }
        mock_post.return_value = auth_response

        response = AnaplanApiExport(mock_http_request)

        assert response.status_code == 500
        assert 'Unexpected API response structure' in response.get_body().decode()


class TestUploadDataToBlob:
    """Test suite for upload_data_to_blob helper function"""

    @patch('function_app.BlobServiceClient')
    def test_upload_data_to_blob_success(self, mock_blob_service):
        """Test successful blob upload"""
        # Setup mocks
        mock_blob_client = Mock()
        mock_blob_service.return_value.get_blob_client.return_value = mock_blob_client

        # Call function
        upload_data_to_blob(
            account_name='testaccount',
            account_key='testkey',
            container_name='testcontainer',
            filename='test/file.csv',
            data=b'test data',
            content_type='text/csv'
        )

        # Verify BlobServiceClient was initialized correctly
        mock_blob_service.assert_called_once_with(
            account_url='https://testaccount.blob.core.windows.net',
            credential='testkey'
        )

        # Verify upload_blob was called
        mock_blob_client.upload_blob.assert_called_once()
        call_args = mock_blob_client.upload_blob.call_args
        assert call_args[0][0] == b'test data'
        assert call_args[1]['blob_type'] == 'BlockBlob'
        assert call_args[1]['overwrite'] is True

    @patch('function_app.BlobServiceClient')
    def test_upload_data_to_blob_default_content_type(self, mock_blob_service):
        """Test blob upload with default content type"""
        mock_blob_client = Mock()
        mock_blob_service.return_value.get_blob_client.return_value = mock_blob_client

        upload_data_to_blob(
            account_name='testaccount',
            account_key='testkey',
            container_name='testcontainer',
            filename='test.txt',
            data=b'test'
        )

        # Verify upload was called
        mock_blob_client.upload_blob.assert_called_once()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
