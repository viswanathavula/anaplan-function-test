import azure.functions as func
import logging
import requests
import time
from azure.storage.blob import BlobServiceClient, ContentSettings

app = func.FunctionApp()

def upload_data_to_blob(account_name: str, account_key: str, container_name: str, filename: str, data: bytes, content_type: str = "text/plain"):
    account_url = f"https://{account_name}.blob.core.windows.net"
    bsc = BlobServiceClient(account_url=account_url, credential=account_key)
    blob_client = bsc.get_blob_client(container=container_name, blob=filename)
    blob_client.upload_blob(
        data,
        blob_type="BlockBlob",
        overwrite=True,
        content_settings=ContentSettings(content_type=content_type),
    )

@app.route(route="AnaplanApiExport", auth_level=func.AuthLevel.ANONYMOUS)
def AnaplanApiExport(req: func.HttpRequest) -> func.HttpResponse:
    try:
        req_body = req.get_json()

        # Validate required parameters
        required_params = [
            'username', 'password', 'account_name', 'account_key', 'container_name',
            'Anaplan_Auth_Url', 'AnaplanExportFile', 'workspace_id', 'model_id',
            'export_id', 'api_url', 'foldername', 'environment'
        ]
        missing_params = [param for param in required_params if not req_body.get(param)]
        if missing_params:
            return func.HttpResponse(
                f"Missing required parameters: {', '.join(missing_params)}",
                status_code=400
            )

        username = req_body.get('username')
        password = req_body.get('password')
        account_name = req_body.get('account_name')
        account_key = req_body.get('account_key')
        container_name = req_body.get('container_name')
        Anaplan_Auth_Url = req_body.get('Anaplan_Auth_Url')
        AnaplanExportFile = req_body.get('AnaplanExportFile')
        workspace_id = req_body.get('workspace_id')
        model_id = req_body.get('model_id')
        export_id = req_body.get('export_id')
        api_url_input = req_body.get('api_url')
        foldername = req_body.get('foldername')
        environment = req_body.get('environment')

        response = requests.post(Anaplan_Auth_Url, auth=(username, password))
        if response.status_code not in (200, 201):
            return func.HttpResponse(f"Failed to authenticate: {response.status_code} {response.text}", status_code=500)
        token_value = response.json()["tokenInfo"]["tokenValue"]
        headers = {"Authorization": f"AnaplanAuthToken {token_value}", "Content-Type": "application/json"}

        export_def_url = f"{api_url_input}/{workspace_id}/models/{model_id}/exports/{export_id}"
        export_def = requests.get(export_def_url, headers=headers)
        if export_def.status_code != 200:
            return func.HttpResponse(f"Failed to get export definition: {export_def.text}", status_code=500)
        file_id = export_def.json()["exportMetadata"]["fileId"]
        logging.info(f"Export {export_id} maps to fileId {file_id}")

        run_url = f"{api_url_input}/{workspace_id}/models/{model_id}/exports/{export_id}/tasks"
        run_resp = requests.post(run_url, headers=headers, json={"localeName": "en_US"})
        if run_resp.status_code not in (200, 201):
            return func.HttpResponse(f"Failed to run export: {run_resp.text}", status_code=500)
        task_id = run_resp.json()["task"]["taskId"]

        task_url = f"{run_url}/{task_id}"
        timeout = time.time() + 600
        while time.time() < timeout:
            task_status = requests.get(task_url, headers=headers)
            state = task_status.json()["task"]["taskState"]
            if state == "COMPLETE":
                break
            elif state == "FAILED":
                return func.HttpResponse("Export task failed", status_code=500)
            time.sleep(10)
        else:
            return func.HttpResponse("Export timed out after 10 minutes.", status_code=504)

        chunks_url = f"{api_url_input}/{workspace_id}/models/{model_id}/files/{file_id}/chunks"
        chunks_resp = requests.get(chunks_url, headers=headers)
        if chunks_resp.status_code != 200:
            return func.HttpResponse(f"Failed to get chunks: {chunks_resp.text}", status_code=500)
        chunk_ids = [c["id"] for c in chunks_resp.json().get("chunks", [])]
        if not chunk_ids:
            return func.HttpResponse("No chunks found for export file.", status_code=500)

        csv_data = b""
        for chunk_id in chunk_ids:
            chunk_url = f"{chunks_url}/{chunk_id}"
            chunk_resp = requests.get(chunk_url, headers=headers)
            csv_data += chunk_resp.content

        blob_path = f"{environment}/Anaplan_Exports/{foldername}/{AnaplanExportFile}"
        upload_data_to_blob(account_name, account_key, container_name, blob_path, csv_data, content_type="text/csv")

        return func.HttpResponse(f"✅ Export {AnaplanExportFile} uploaded successfully!", status_code=200)

    except ValueError as e:
        logging.error(f"Invalid JSON in request body: {str(e)}")
        return func.HttpResponse("Invalid JSON in request body", status_code=400)
    except KeyError as e:
        logging.error(f"Missing key in response: {str(e)}")
        return func.HttpResponse(f"Unexpected API response structure: {str(e)}", status_code=500)
    except Exception as e:
        logging.exception("Error in AnaplanApiExport")
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)
