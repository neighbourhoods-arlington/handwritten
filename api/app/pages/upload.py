"""Server-rendered /upload page (plain HTML, no frontend build needed).

Contains a single file input and a "Renew" button to upload donor/gift data.
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["pages"], include_in_schema=False)

UPLOAD_PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Upload</title>
  <style>
    :root { color-scheme: light dark; font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
    body { margin: 0; padding: 0 16px; }
    main { max-width: 560px; margin: 48px auto; }
    h1 { font-size: 1.5rem; margin-bottom: 24px; }
    form { display: grid; gap: 16px; }
    label { display: grid; gap: 8px; }
    input[type="file"] { padding: 10px; border: 1px dashed color-mix(in srgb, currentColor 40%, transparent); border-radius: 8px; }
    button { justify-self: start; padding: 10px 20px; border: 0; border-radius: 8px; background: #2563eb; color: #fff; font-size: 1rem; cursor: pointer; }
    button:hover { background: #1d4ed8; }
    .hint { opacity: 0.8; font-size: 0.9rem; }
    .success { color: #16a34a; }
    .error { color: #dc2626; }
  </style>
</head>
<body>
  <main>
    <h1>Upload</h1>
    <form id="upload-form">
      <label>
        File
        <input type="file" id="file" name="file" accept=".csv" required>
      </label>
      <button type="submit" id="renew">Renew</button>
      <p class="hint" id="status">Please select a CSV file and click Renew.</p>
    </form>
  </main>
  <script>
    document.getElementById("upload-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      
      const fileInput = document.getElementById("file");
      const statusEl = document.getElementById("status");
      
      if (fileInput.files.length === 0) {
        statusEl.className = "hint error";
        statusEl.textContent = "Please select a file first.";
        return;
      }

      const formData = new FormData();
      formData.append("file", fileInput.files[0]);

      statusEl.className = "hint";
      statusEl.textContent = "Uploading and processing...";

      try {
        const response = await fetch("/api/v1/imports/", {
          method: "POST",
          body: formData
        });

        const result = await response.json();

        if (response.ok) {
          statusEl.className = "hint success";
          statusEl.textContent = `Success! Rows read: ${result.rows_read}, Donors inserted: ${result.donors_inserted}`;
        } else {
          statusEl.className = "hint error";
          statusEl.textContent = "Error: " + (result.detail || "Unknown error occurred");
        }
      } catch (error) {
        statusEl.className = "hint error";
        statusEl.textContent = "Server connection error.";
        console.error(error);
      }
    });
  </script>
</body>
</html>
"""


@router.get("/upload", response_class=HTMLResponse)
async def upload_page() -> HTMLResponse:
    return HTMLResponse(UPLOAD_PAGE)