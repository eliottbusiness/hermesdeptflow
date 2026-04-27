from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import ClientConfig
from .models import CRM_COLUMNS, PipelineStatus, ScoringResult
from .utils import stable_id


class CRMError(RuntimeError):
    pass


class GoogleSheetsCRM:
    def __init__(self, config: ClientConfig) -> None:
        self.config = config
        self._service: Any | None = None
        self._drive: Any | None = None

    @property
    def spreadsheet_id(self) -> str:
        return self.config.google.spreadsheet_id

    def _credentials(self) -> Any:
        from google.oauth2 import service_account

        path = self.config.google.service_account_file
        if not path:
            raise CRMError("GOOGLE_APPLICATION_CREDENTIALS ou google.service_account_file manquant")
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.file",
        ]
        return service_account.Credentials.from_service_account_file(path, scopes=scopes)

    def sheets_service(self) -> Any:
        if self._service is None:
            from googleapiclient.discovery import build

            self._service = build("sheets", "v4", credentials=self._credentials(), cache_discovery=False)
        return self._service

    def drive_service(self) -> Any:
        if self._drive is None:
            from googleapiclient.discovery import build

            self._drive = build("drive", "v3", credentials=self._credentials(), cache_discovery=False)
        return self._drive

    def setup(self) -> str:
        if self.config.google.spreadsheet_id:
            self.ensure_tabs()
            return self.config.google.spreadsheet_id
        service = self.sheets_service()
        body = {
            "properties": {"title": self.config.google.spreadsheet_title},
            "sheets": [
                {"properties": {"title": self.config.google.prospects_tab}},
                {"properties": {"title": self.config.google.rejected_tab}},
            ],
        }
        created = service.spreadsheets().create(body=body, fields="spreadsheetId,spreadsheetUrl").execute()
        self.config.google.spreadsheet_id = created["spreadsheetId"]
        self._move_to_client_folder(created["spreadsheetId"])
        self.ensure_tabs()
        return str(created.get("spreadsheetUrl") or created["spreadsheetId"])

    def ensure_tabs(self) -> None:
        self._ensure_sheet(self.config.google.prospects_tab)
        self._ensure_sheet(self.config.google.rejected_tab)
        self._write_header(self.config.google.prospects_tab)
        self._write_header(self.config.google.rejected_tab)

    def _ensure_sheet(self, tab: str) -> None:
        service = self.sheets_service()
        meta = service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()
        titles = {sheet.get("properties", {}).get("title") for sheet in meta.get("sheets", [])}
        if tab in titles:
            return
        service.spreadsheets().batchUpdate(
            spreadsheetId=self.spreadsheet_id,
            body={"requests": [{"addSheet": {"properties": {"title": tab}}}]},
        ).execute()

    def _move_to_client_folder(self, spreadsheet_id: str) -> None:
        folder_name = self.config.google.drive_folder_name
        if not folder_name:
            return
        drive = self.drive_service()
        query = (
            "mimeType='application/vnd.google-apps.folder' "
            f"and name='{folder_name}' and trashed=false"
        )
        folders = drive.files().list(q=query, fields="files(id,name)", spaces="drive").execute().get("files", [])
        if folders:
            folder_id = folders[0]["id"]
        else:
            folder = drive.files().create(
                body={"name": folder_name, "mimeType": "application/vnd.google-apps.folder"},
                fields="id",
            ).execute()
            folder_id = folder["id"]
        file_meta = drive.files().get(fileId=spreadsheet_id, fields="parents").execute()
        previous_parents = ",".join(file_meta.get("parents", []))
        drive.files().update(
            fileId=spreadsheet_id,
            addParents=folder_id,
            removeParents=previous_parents,
            fields="id, parents",
        ).execute()

    def _write_header(self, tab: str) -> None:
        service = self.sheets_service()
        service.spreadsheets().values().update(
            spreadsheetId=self.spreadsheet_id,
            range=f"{tab}!A1:U1",
            valueInputOption="RAW",
            body={"values": [CRM_COLUMNS]},
        ).execute()
        requests = [
            {
                "repeatCell": {
                    "range": {"sheetId": self._sheet_id(tab), "startRowIndex": 0, "endRowIndex": 1},
                    "cell": {
                        "userEnteredFormat": {
                            "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                            "backgroundColor": {"red": 0.05, "green": 0.17, "blue": 0.35},
                        }
                    },
                    "fields": "userEnteredFormat(backgroundColor,textFormat)",
                }
            }
        ]
        service.spreadsheets().batchUpdate(
            spreadsheetId=self.spreadsheet_id, body={"requests": requests}
        ).execute()

    def _sheet_id(self, tab: str) -> int:
        service = self.sheets_service()
        meta = service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()
        for sheet in meta.get("sheets", []):
            props = sheet.get("properties", {})
            if props.get("title") == tab:
                return int(props.get("sheetId"))
        raise CRMError(f"Onglet introuvable: {tab}")

    def existing_linkedin_urls(self) -> set[str]:
        values = self._get_values(f"{self.config.google.prospects_tab}!A2:U")
        url_index = CRM_COLUMNS.index("url_linkedin")
        return {row[url_index] for row in values if len(row) > url_index and row[url_index]}

    def append_results(self, results: list[ScoringResult]) -> tuple[int, int]:
        existing = self.existing_linkedin_urls()
        to_add: list[list[Any]] = []
        dedup = 0
        for result in results:
            if not result.qualified:
                continue
            url = result.prospect.linkedin_url
            if url in existing:
                dedup += 1
                continue
            to_add.append(result_to_row(result))
            existing.add(url)
        if to_add:
            self.sheets_service().spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range=f"{self.config.google.prospects_tab}!A:U",
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body={"values": to_add},
            ).execute()
        return len(to_add), dedup

    def update_connection_sent(self, linkedin_url: str) -> bool:
        values = self._get_values(f"{self.config.google.prospects_tab}!A2:U")
        url_index = CRM_COLUMNS.index("url_linkedin")
        status_index = CRM_COLUMNS.index("statut")
        sent_index = CRM_COLUMNS.index("date_connexion_envoyee")
        for idx, row in enumerate(values, start=2):
            if len(row) > url_index and row[url_index] == linkedin_url:
                self.sheets_service().spreadsheets().values().batchUpdate(
                    spreadsheetId=self.spreadsheet_id,
                    body={
                        "valueInputOption": "USER_ENTERED",
                        "data": [
                            {
                                "range": f"{self.config.google.prospects_tab}!{_col(status_index)}{idx}",
                                "values": [[PipelineStatus.CONNECTION_SENT.value]],
                            },
                            {
                                "range": f"{self.config.google.prospects_tab}!{_col(sent_index)}{idx}",
                                "values": [[datetime.now(tz=UTC).date().isoformat()]],
                            },
                        ],
                    },
                ).execute()
                return True
        return False

    def _get_values(self, range_name: str) -> list[list[str]]:
        result = self.sheets_service().spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id, range=range_name
        ).execute()
        return result.get("values", [])


class LocalCSVCRM:
    """Offline/dry-run CRM adapter used for local QA and demos."""

    def __init__(self, config: ClientConfig, path: str | Path = "runs/local-crm.csv") -> None:
        self.config = config
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text(",".join(CRM_COLUMNS) + "\n", encoding="utf-8")

    def append_results(self, results: list[ScoringResult]) -> tuple[int, int]:
        existing = self.existing_linkedin_urls()
        lines: list[str] = []
        dedup = 0
        for result in results:
            if not result.qualified:
                continue
            if result.prospect.linkedin_url in existing:
                dedup += 1
                continue
            row = [str(v).replace("\n", " ").replace(",", ";") for v in result_to_row(result)]
            lines.append(",".join(row))
            existing.add(result.prospect.linkedin_url)
        if lines:
            with self.path.open("a", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
        return len(lines), dedup

    def update_connection_sent(self, linkedin_url: str) -> bool:
        return bool(linkedin_url)

    def existing_linkedin_urls(self) -> set[str]:
        rows = self.path.read_text(encoding="utf-8").splitlines()[1:]
        idx = CRM_COLUMNS.index("url_linkedin")
        urls = set()
        for row in rows:
            parts = row.split(",")
            if len(parts) > idx:
                urls.add(parts[idx])
        return urls


def result_to_row(result: ScoringResult) -> list[Any]:
    p = result.prospect
    today = datetime.now(tz=UTC).date().isoformat()
    return [
        stable_id(p.linkedin_url, p.full_name, p.company),
        today,
        p.first_name,
        p.last_name,
        p.title,
        p.company,
        p.linkedin_url,
        p.location,
        p.industry,
        p.company_size,
        result.status.value,
        result.nb_signaux_activite,
        result.nb_signaux_intention,
        result.priorite_interne,
        " | ".join(result.signaux_detectes),
        result.dernier_post.isoformat() if result.dernier_post else "",
        result.pipeline_status.value,
        "",
        "",
        result.llm_explanation,
        today,
    ]


def _col(index_zero_based: int) -> str:
    n = index_zero_based + 1
    out = ""
    while n:
        n, remainder = divmod(n - 1, 26)
        out = chr(65 + remainder) + out
    return out
