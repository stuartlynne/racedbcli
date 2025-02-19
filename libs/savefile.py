
import sys
import os


def save_file(final_response, filename=None):
    
    # 4) Determine filename from 'Content-Disposition' if present
    content_disp = final_response.headers.get("Content-Disposition", "")
    print(f"Content-Disposition: {content_disp}", file=sys.stdout)
    if not filename:
        if "filename=" in content_disp:
            # e.g. Content-Disposition: attachment; filename="export.xlsx"
            parts = content_disp.split("filename=")
            if len(parts) > 1:
                raw_fn = parts[1].strip().strip(';').strip('"').strip()
                filename = os.path.basename(raw_fn)

    if not filename:
        # Fallback name
        filename = "downloaded_file.xlsx"

    out_path = os.path.join(".", filename)
    print(f"Writing downloaded content to {out_path}", file=sys.stdout)

    # If the response was 302, sometimes the actual content might come from the final location.
    # Typically requests automatically follows the redirect, so the final_response is the file.
    # We'll write out the content from final_response.
    with open(out_path, "wb") as f:
        for chunk in final_response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    return out_path
