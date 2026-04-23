import os
import time
import pandas as pd
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP
mcp = FastMCP("Filesystem Server")

# Set the base path for clinical trial data
BASE_PATH = os.getenv("TRIAL_DATA_PATH", "./trial_data")
BASE_ABS = os.path.abspath(BASE_PATH)

def _safe_path(path: str) -> str:
    """Ensures the LLM cannot access files outside the trial_data directory."""
    full = os.path.abspath(os.path.join(BASE_ABS, path))
    if not full.startswith(BASE_ABS):
        raise ValueError("Security Violation: Access outside trial data folder is restricted.")
    return full

@mcp.tool()
def list_directory(path: str = ".") -> dict:
    """
    List all files and subdirectories inside the clinical trial data folder.
    Use this to explore the folder structure (e.g., 'sdtm' or 'documents').
    """
    try:
        full_path = _safe_path(path)
        if not os.path.exists(full_path):
            return {"error": f"Path '{path}' does not exist."}

        items = os.listdir(full_path)
        files = [f for f in items if os.path.isfile(os.path.join(full_path, f))]
        dirs = [d for d in items if os.path.isdir(os.path.join(full_path, d))]

        return {
            "current_path": path,
            "files": files,
            "directories": dirs,
            "summary": f"Found {len(files)} files and {len(dirs)} directories."
        }
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def read_file(filename: str) -> dict:
    """
    Read the contents of a clinical document (TXT, PDF) or a dataset (CSV).
    Automatically detects file type and returns structured data for CSVs.
    """
    try:
        # Search for file recursively if path isn't explicit
        target_file = None
        for root, _, files in os.walk(BASE_PATH):
            if filename in files:
                target_file = os.path.join(root, filename)
                break
        
        if not target_file:
            return {"error": f"File '{filename}' not found in trial_data."}

        # CSV Processing
        if filename.lower().endswith(".csv"):
            df = pd.read_csv(target_file)
            return {
                "type": "dataset",
                "filename": filename,
                "row_count": len(df),
                "columns": list(df.columns),
                "data": df.head(50).to_dict(orient="records") # Limit to 50 rows for LLM context
            }

        # PDF Processing
        if filename.lower().endswith(".pdf"):
            import PyPDF2
            with open(target_file, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                text = "\n".join(page.extract_text() or "" for page in reader.pages)
            return {"type": "document", "filename": filename, "content": text}

        # Standard Text Processing
        with open(target_file, "r", encoding="utf-8", errors="ignore") as f:
            return {"type": "document", "filename": filename, "content": f.read()}

    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def write_file(filename: str, content: str, subfolder: str = "documents") -> dict:
    """
    Create or update a file in the trial data folder. 
    Use this to save generated safety reports, clinical summaries, or study notes.
    """
    try:
        # Ensure the subfolder exists (e.g., trial_data/documents)
        folder_path = _safe_path(subfolder)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            
        file_path = os.path.join(folder_path, filename)
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        return {"status": "success", "message": f"File '{filename}' saved successfully in {subfolder}."}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def search_files(keyword: str) -> dict:
    """
    Search for a specific clinical term (e.g., 'Hypertension', 'Serious AE') 
    across all files in the trial data repository.
    """
    try:
        results = []
        key = keyword.lower()

        for root, _, files in os.walk(BASE_PATH):
            for filename in files:
                filepath = os.path.join(root, filename)
                try:
                    # Skip binary files, focus on text/csv
                    if not filename.lower().endswith(('.txt', '.csv', '.json', '.log')):
                        continue
                        
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                        
                    matches = [
                        {"line_num": i+1, "text": line.strip()}
                        for i, line in enumerate(lines)
                        if key in line.lower()
                    ]
                    
                    if matches:
                        results.append({
                            "file": filename,
                            "matches": matches[:3] # Return top 3 matches per file
                        })
                except:
                    continue

        return {"search_term": keyword, "files_with_matches": len(results), "results": results}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def watch_folder() -> dict:
    """
    Check for files modified within the last hour. 
    Use this to identify 'live' updates or newly arrived clinical reports.
    """
    try:
        recent = []
        now = time.time()

        for root, _, files in os.walk(BASE_PATH):
            for filename in files:
                filepath = os.path.join(root, filename)
                mtime = os.path.getmtime(filepath)

                if now - mtime < 3600: # 1 hour
                    recent.append({
                        "file": filename,
                        "folder": os.path.relpath(root, BASE_PATH),
                        "modified_ago_minutes": round((now - mtime) / 60, 1)
                    })

        return {"new_or_updated_files": recent, "count": len(recent)}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    mcp.run(transport="stdio")