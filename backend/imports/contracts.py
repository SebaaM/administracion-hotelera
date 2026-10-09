from typing import TypedDict, NotRequired

class SourceCell(TypedDict):
    ref: str
    row: int
    col: int
    value: str
    note: str
    color: str | None
    kind: str

class SheetConfig(TypedDict):
    name: str
    year: int
    month: int
    label_col: int
    header_rows: list[int]
    unit_rows: list[int]

class WorkbookSource(TypedDict):
    format: str
    sheets: list[dict]
    candidates: NotRequired[list[dict]]

class Candidate(TypedDict):
    key: str
    source_id: str
    source_unit: str
    guest: str
    start: str
    end: str
    notes: list[dict]
    colors: list[dict]
    references: list[dict]
    warnings: list[str]
    status: NotRequired[str]

class RowDecision(TypedDict, total=False):
    selected: bool
    guest: str
    start: str
    end: str
    status: str
    unit_id: int
    reservation_id: int | None
    reviewed: bool
    new_confirmed: bool

class NoteDecision(TypedDict):
    action: str
    target: NotRequired[str]
    reason: NotRequired[str]

class PreviewRow(TypedDict):
    key: str
    action: str
    errors: list[str]
    candidate: dict
    before: dict | None
    snapshot: str
    selected: bool

class Preview(TypedDict):
    rows: list[PreviewRow]
    pending_notes: list[dict]
    summary: dict
