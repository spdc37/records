import json
import os
from datetime import datetime
from typing import List, Dict, Any

from google.oauth2 import service_account
from googleapiclient.discovery import build


SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


def get_service_account_credentials():
    raw = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not raw:
        raise RuntimeError(
            "GOOGLE_SERVICE_ACCOUNT_JSON environment variable is not set"
        )

    try:
        info = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON is not valid JSON") from exc

    return service_account.Credentials.from_service_account_info(info, scopes=SCOPES)


def fetch_sheet_values(
    service, spreadsheet_id: str, range_name: str, include_people: bool = False
) -> List[Dict[str, Any]]:
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=range_name)
        .execute()
    )
    values = result.get("values", [])
    if not values:
        return []

    headers = values[0]
    rows = values[1:]

    mapped_rows: List[Dict[str, Any]] = []
    for row in rows:
        if not any(isinstance(cell, str) and cell.strip() for cell in row):
            continue

        row_dict = {
            header: row[idx] if idx < len(row) else ""
            for idx, header in enumerate(headers)
        }

        item: Dict[str, Any] = {
            "artist": row_dict.get("Artiste", ""),
            "album": row_dict.get("Album", ""),
            "genre": row_dict.get("Genre", ""),
            "year": row_dict.get("Annee", ""),
        }

        if include_people:
            # Column E (index 4) stores a multi-select dropdown of people.
            raw_people = ""
            if len(row) > 4 and isinstance(row[4], str):
                raw_people = row[4]

            # Google Sheets multi-select dropdowns are comma-separated.
            # Also handle possible newlines robustly.
            tokens = raw_people.replace("\n", ",").split(",") if raw_people else []
            people = [t.strip() for t in tokens if t.strip()]
            item["people"] = people

        mapped_rows.append(item)

    return mapped_rows


def build_payload(items):
    # Use local time, assuming server TZ is Europe/Paris
    now = datetime.now().astimezone()
    return {
        "updated_at": now.isoformat(),
        "items": items,
    }


def write_json(path: str, data) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def main() -> None:
    spreadsheet_id = os.getenv("SPREADSHEET_ID")
    if not spreadsheet_id:
        raise RuntimeError("SPREADSHEET_ID environment variable is not set")

    creds = get_service_account_credentials()
    service = build("sheets", "v4", credentials=creds, cache_discovery=False)

    collection_items = fetch_sheet_values(service, spreadsheet_id, "collection!A:D")
    # Wantlist has an extra E column with people multi-select
    wantlist_items = fetch_sheet_values(
        service, spreadsheet_id, "wantlist!A:E", include_people=True
    )

    collection = build_payload(collection_items)
    wantlist = build_payload(wantlist_items)

    write_json("collection.json", collection)
    write_json("wantlist.json", wantlist)


if __name__ == "__main__":
    main()
