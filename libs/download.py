#!/usr/bin/env python3

import sys
import os
import io
import json
import gzip
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def download_file(racedb, download_url=None, data=None):
    """
    1) GET the page at base_url/download_url (which contains the form).
    2) Parse out the csrfmiddlewaretoken from the hidden input.
    3) POST to the same page (or form action) with:
       - csrfmiddlewaretoken
       - <button>=<value>
    4) Write the downloaded file to disk, using either the server-provided filename
       or a default if not provided.

    :param session: A requests.Session() with any needed cookies already set.
    :param base_url: e.g. "http://192.168.250.51:9080"
    :param download_url: e.g. "RaceDB/NumberSets/NumbersetEdit/51/NumberSetManage/51/"
    :param button: e.g. "excel-export-submit"
    :param value: e.g. "Export to Excel"
    :param output_dir: Directory in which to save the downloaded file (default: current).
    :return: The path to the downloaded file, or None if download failed.
    """

    # 1) Construct URL and GET the form page
    page_url = f"{racedb.base_url.rstrip('/')}/{download_url.lstrip('/')}"
    print(f"GET {page_url}", file=sys.stdout)
    r_get = racedb.session.get(page_url)
    print('Status code:', r_get.status_code)
    if r_get.status_code != 200:
        print(f"Failed to GET page: {r_get.status_code}", file=sys.stdout)
        print(r_get.text, file=sys.stdout)
        return None

    # 2) Parse out the CSRF token from <input type="hidden" name="csrfmiddlewaretoken" value="...">
    soup = BeautifulSoup(r_get.text, "html.parser")
    csrf_input = soup.find("input", {"name": "csrfmiddlewaretoken"})
    if not csrf_input:
        print("Could not find 'csrfmiddlewaretoken' in the page.", file=sys.stdout)
        return None
    csrf_token = csrf_input.get("value")

    # Find the form's 'action' attribute.
    # Some pages might have <form action="."> or just "action="" (same page).
    form = soup.find("form", {"method": "post"})
    if not form:
        print("Could not find <form method='post'> in the page.", file=sys.stdout)
        return None

    action_attr = form.get("action", "").strip()
    if action_attr:
        post_url = urljoin(page_url, action_attr)
    else:
        # If action is empty, use the same page_url
        post_url = page_url


    # 3) POST data with the specified button name/value, and the CSRF token
    if not data:
        data = {}
    data["csrfmiddlewaretoken"] = csrf_token,
    headers = {
        "Referer": page_url
    }
    print(f"POST to {post_url} data:{data}", file=sys.stdout)

    r_post = racedb.session.post(post_url, data=data, headers=headers, stream=True)
    # stream=True so we can download file in chunks

    if r_post.status_code not in (200, 201, 202, 302):
        print(f"File download failed (status={r_post.status_code}).", file=sys.stdout)
        print(r_post.text, file=sys.stdout)
        return None
    return r_post

    # If it’s a 302 redirect, follow that (some Django views might redirect to a file response).
    # requests will automatically follow redirects if we haven't disabled it, 
    # but if you need to handle the final destination manually, do so here.
    #final_response = r_post
    #if final_response.history and final_response.status_code == 200:
    #    # final_response is after redirect
    #    return final_response
    #return final_response

    # 4) Determine filename from 'Content-Disposition' if present
    content_disp = final_response.headers.get("Content-Disposition", "")
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

    out_path = os.path.join(output_dir, filename)
    print(f"Writing downloaded content to {out_path}", file=sys.stdout)

    if downloadJSON:
        with gzip.GzipFile(fileobj=io.BytesIO(final_response.content), mode='rb') as f:
            decompressed = f.read()
            return json.loads(decompressed)

    # If the response was 302, sometimes the actual content might come from the final location.
    # Typically requests automatically follows the redirect, so the final_response is the file.
    # We'll write out the content from final_response.
    with open(out_path, "wb") as f:
        for chunk in final_response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    print("Download completed successfully!", file=sys.stdout)
    return out_path


