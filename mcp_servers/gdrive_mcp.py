import os
import io
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
import json

load_dotenv()

# Initialize FastMCP for Google Drive
mcp = FastMCP("GoogleDrive Server")

def get_drive_service():
    """Service Account authentication for Google Drive (Cloud-safe)."""
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    import streamlit as st
    import json

    scopes = ["https://www.googleapis.com/auth/drive.readonly"]

    # ✅ ONLY use JSON from secrets
    if "GOOGLE_CREDENTIALS_JSON" in st.secrets:
        info = json.loads(st.secrets["GOOGLE_CREDENTIALS_JSON"])
        creds = service_account.Credentials.from_service_account_info(
            info,
            scopes=scopes
        )
    else:
        raise Exception("GOOGLE_CREDENTIALS_JSON missing in secrets")

    return build("drive", "v3", credentials=creds)

@mcp.tool()
def list_drive_files(query: str = "") -> dict:
    """
    List files available in the Google Drive. 
    - If 'query' is EMPTY, it lists all files in the ROOT directory.
    - If 'query' is provided, it filters files by name.
    Use this to browse for clinical trial documents, protocols, or reports.
    """
    try:
        service = get_drive_service()
        
        # If no query is provided, explicitly list files in the 'root' folder.
        # We also ensure trashed files are ignored for accuracy.
        if not query or not query.strip():
            q = "trashed = false"
        else:
            safe_query = query.replace("'", "\\'")
            q = f"name contains '{safe_query}' and trashed = false"
            
        results = service.files().list(
            q=q,
            pageSize=50, # Increased page size to ensure more files are visible at once
            fields="files(id, name, mimeType, modifiedTime, size)"
        ).execute()
        
        files = results.get("files", [])
        
        return {
            "query_used": query if query else "None (Listing Root)",
            "total_found": len(files),
            "files": files,
            "message": "If you cannot find a specific file, try using the search_drive_files tool for a deep search."
        }
    except Exception as e:
        return {"error": f"Drive API Error: {str(e)}"}

@mcp.tool()
def read_drive_file(file_id: str) -> dict:
    """
    Download and read the content of a Google Drive file using its unique ID.
    Supports Google Docs (converted to text) and standard text/PDF files.
    """
    try:
        from googleapiclient.http import MediaIoBaseDownload

        service = get_drive_service()
        # Fetch metadata first to determine how to handle the file
        meta = service.files().get(fileId=file_id, fields="name,mimeType").execute()
        name = meta.get("name", "unknown_file")
        mime = meta.get("mimeType", "")

        # Handle native Google Docs (must be exported as text)
        if "google-apps.document" in mime:
            content = service.files().export(fileId=file_id, mimeType="text/plain").execute()
            return {
                "file_id": file_id,
                "filename": name,
                "mime_type": mime,
                "content": content.decode("utf-8", errors="ignore")
            }

        # Handle standard files (PDFs, TXT, CSV)
        request = service.files().get_media(fileId=file_id)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False

        while not done:
            status, done = downloader.next_chunk()

        # Attempt to decode text content for the LLM
        raw_bytes = buffer.getvalue()
        try:
            content = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            # If the file is a PDF or binary, the raw text may not be readable here.
            # The LLM can still use the filename and metadata to confirm its existence.
            content = f"[Binary content or PDF detected ({len(raw_bytes)} bytes). Content cannot be displayed as plain text.]"

        return {
            "file_id": file_id,
            "filename": name,
            "mime_type": mime,
            "content": content
        }
    except Exception as e:
        return {"error": f"Read Error: {str(e)}"}

@mcp.tool()
def search_drive_files(keyword: str) -> dict:
    """
    Perform a deep search on Google Drive for a specific clinical keyword.
    Searches both file names and the internal text content of documents.
    """
    try:
        service = get_drive_service()
        # Search metadata and full text while excluding the trash
        safe_keyword = keyword.replace("'", "\\'")
        q = f"(name contains '{safe_keyword}' or fullText contains '{safe_keyword}') and trashed = false"
        
        results = service.files().list(
            q=q,
            pageSize=20,
            fields="files(id, name, mimeType, modifiedTime)"
        ).execute()
        
        files = results.get("files", [])
        return {
            "search_keyword": keyword,
            "matches_found": len(files),
            "results": files
        }
    except Exception as e:
        return {"error": f"Search Error: {str(e)}"}

if __name__ == "__main__":
    mcp.run(transport="stdio")