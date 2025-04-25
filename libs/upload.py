
import sys
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from libs.lib import yprint, gprint

def upload_file(racedb, next_path, data=None, files=None, tableCheck=False, preCheck=False, ):

    # 1. GET the upload form page
    upload_form_url = f"{racedb.base_url.rstrip('/')}/{next_path.lstrip('/')}"
    gprint(f"=== GET to upload form page: {upload_form_url}", file=sys.stdout)
    r_get_upload = racedb.session.get(upload_form_url)
    if r_get_upload.status_code != 200:
        yprint("Could not load upload form page successfully.", file=sys.stdout)
        print(r_get_upload.text, file=sys.stdout)
        return

    # 2. Parse out the CSRF token for the upload form
    soup_upload = BeautifulSoup(r_get_upload.text, "html.parser")
    csrf_input_upload = soup_upload.find("input", {"name": "csrfmiddlewaretoken"})
    if not csrf_input_upload:
        yprint("Could not find 'csrfmiddlewaretoken' in the upload form.", file=sys.stdout)
        return
    csrf_token = csrf_input_upload.get("value")

    # 3. Find the <form> and get its action attribute
    upload_form = soup_upload.find("form")
    if not upload_form:
        yprint("Could not find <form> element on the upload page.", file=sys.stdout)
        return

    action_attr = upload_form.get("action", "").strip()
    # If action is empty, post back to the same URL; otherwise, combine it properly
    if action_attr:
        upload_action_url = urljoin(upload_form_url, action_attr)
    else:
        upload_action_url = upload_form_url

    gprint(f"Upload form action: {upload_action_url}", file=sys.stdout)

    # 4. Prepare the form data
    #
    # For each checkbox:
    #   - If checked in the browser, include `name: "on"` in data.
    #   - If unchecked in the browser, do NOT include it at all.
    #
    # Example checkboxes from your HTML:
    #   name="set_team_all_disciplines"  (checked by default)
    #   name="replace_tags"             (unchecked by default)
    #   name="replace_bibs"             (unchecked by default)
    #   name="update_license_codes"     (checked by default)
    #
    # Also note there's a submit button with:
    #   name="ok-submit"  value="OK"
    #
    # The simplest approach: only include the checkboxes that are checked.
    #
    if data is None:
        data = {}

    data["csrfmiddlewaretoken"] = csrf_token,
  
    headers = {"Referer": upload_form_url}

    #files = { filetype: open(file_path, "rb") }
    headers_upload = {"Referer": upload_form_url}

    gprint(f"=== POST file to: {upload_action_url} data: {data}", file=sys.stdout)
    r_post_upload = racedb.session.post(
        upload_action_url,
        data=data,
        files=files,
        headers=headers_upload
    )

    if r_post_upload.status_code not in (200, 201, 302):
        yprint("File upload may have failed.", file=sys.stdout)
        print(r_post_upload.text, file=sys.stdout)
        return

    # 5. Find the table and print minimal text
    soup_response = BeautifulSoup(r_post_upload.text, "html.parser")

    if tableCheck:
        # Look for the <table> with your known classes (from the example).
        # Adjust if your server's HTML uses different classes/identifiers.
        table = soup_response.find("table", {
            "class": "table table-hover table-sm table-condensed"
        })
        if table:
            gprint("=== Upload Result Table ===", file=sys.stdout)
            print_table_as_text(table)
            return
        preCheck = True
    if preCheck:
        pre_block = soup_response.find("pre")
        if pre_block:
            gprint("=== Upload Summary ===", file=sys.stdout)
            #print(pre_block.get_text(strip=True), file=sys.stdout)
            lines = pre_block.get_text(strip=True).split("\n")
            for line in lines:
                if line.startswith("* Row"):
                    print(line, file=sys.stdout)
                else:
                    yprint(line, file=sys.stdout)
        else:
            yprint("No <pre> block found in response page.", file=sys.stdout)
            print(r_post_upload.text, file=sys.stdout)
            return


def print_table_as_text(table):
    """
    Parses an HTML <table> and prints its contents with minimal formatting:
    - Vertical bars between columns
    - One row per line
    """
    # Try to parse the header row
    thead = table.find("thead")
    if thead:
        header_cells = thead.find_all("th")
        header_texts = [th.get_text(strip=True) for th in header_cells]
        # Print header row if it has any content
        if header_texts:
            print(" | ".join(header_texts), file=sys.stdout)

    # Now parse all <tr> in the table body (or entire <table> if no <tbody>)
    tbody = table.find("tbody")
    if not tbody:
        rows = table.find_all("tr")
    else:
        rows = tbody.find_all("tr")

    # For each row, get <td> text
    for tr in rows:
        tds = tr.find_all("td")
        if not tds:
            continue
        row_cells = [td.get_text(strip=True) for td in tds]
        print(" | ".join(row_cells), file=sys.stdout)


