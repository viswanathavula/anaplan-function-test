# Anaplan Export to Azure Blob Storage Function

This Azure Function exports data from Anaplan and uploads it to Azure Blob Storage.

## Overview

This function authenticates with Anaplan API, triggers an export, waits for completion, downloads the exported data in chunks, and uploads it to Azure Blob Storage.

## Prerequisites

- Python 3.8 or higher
- Azure Functions Core Tools
- Azure Storage Account
- Anaplan account with API access

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

The function expects the following parameters in the HTTP POST request body:

### Required Parameters

- `username`: Anaplan username
- `password`: Anaplan password
- `account_name`: Azure Storage account name
- `account_key`: Azure Storage account key
- `container_name`: Azure Blob Storage container name
- `Anaplan_Auth_Url`: Anaplan authentication URL
- `AnaplanExportFile`: Name of the export file
- `workspace_id`: Anaplan workspace ID
- `model_id`: Anaplan model ID
- `export_id`: Anaplan export ID
- `api_url`: Anaplan API base URL
- `foldername`: Folder name in blob storage
- `environment`: Environment name (e.g., dev, prod)

## Usage

### Local Development

1. Update `local.settings.json` with your configuration
2. Run the function locally:
   ```bash
   func start
   ```

### Deployment

Deploy to Azure using Azure Functions Core Tools:
```bash
func azure functionapp publish <FUNCTION_APP_NAME>
```

## API Endpoint

**POST** `/api/AnaplanApiExport`

### Request Body Example

```json
{
  "username": "your-anaplan-username",
  "password": "your-anaplan-password",
  "account_name": "your-storage-account",
  "account_key": "your-storage-key",
  "container_name": "your-container",
  "Anaplan_Auth_Url": "https://auth.anaplan.com/token/authenticate",
  "AnaplanExportFile": "export_data.csv",
  "workspace_id": "workspace-id",
  "model_id": "model-id",
  "export_id": "export-id",
  "api_url": "https://api.anaplan.com/2/0/workspaces",
  "foldername": "exports",
  "environment": "production"
}
```

### Response

- **200**: Export uploaded successfully
- **400**: Missing required parameters or invalid JSON
- **500**: Server error (authentication failed, export failed, etc.)
- **504**: Export timeout (exceeded 10 minutes)

## Error Handling

The function includes comprehensive error handling for:
- Missing required parameters
- Authentication failures
- Export task failures
- Timeout scenarios (10-minute limit)
- Invalid JSON requests
- API response structure issues

## Security Considerations

⚠️ **Important**: This function accepts credentials in the request body. Consider implementing:
- Azure Key Vault for storing credentials
- Managed Identity for Azure resources
- API authentication (change `auth_level` from `ANONYMOUS`)
- Request validation and sanitization
- Network restrictions (firewall rules)

## File Structure

```
.
├── function_app.py          # Main function code
├── AnaplanApiExport/        
│   └── function.json        # Function binding configuration
├── requirements.txt         # Python dependencies
├── host.json               # Function host configuration
├── local.settings.json     # Local development settings
└── README.md              # This file
```

## Development

### Running Tests

Currently, there is no test infrastructure. Consider adding:
- Unit tests for individual functions
- Integration tests for the full workflow
- Mock tests for external API calls

### Code Quality

Ensure code quality by:
- Running linters (flake8, pylint)
- Formatting code (black)
- Type checking (mypy)

## Troubleshooting

### Common Issues

1. **Authentication failure**: Verify Anaplan credentials and API URL
2. **Export timeout**: Increase timeout or optimize export size
3. **Blob upload failure**: Check Azure Storage credentials and permissions
4. **Missing chunks**: Verify export completed successfully

### Logging

The function logs important events and errors. Check:
- Azure Function logs in the portal
- Application Insights for detailed telemetry
- Console output during local development

## License

[Add your license information here]

## Contributing

[Add contribution guidelines here]
