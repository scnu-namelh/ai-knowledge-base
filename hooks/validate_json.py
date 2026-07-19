#!/usr/bin/env python3
"""Validate knowledge entry JSON files."""

import json
import re
import sys
from pathlib import Path
from typing import Any


REQUIRED_FIELDS: dict[str, type] = {
    "id": str,
    "title": str,
    "source_url": str,
    "summary": str,
    "tags": list,
    "status": str,
}

VALID_STATUSES = frozenset({"pending", "analyzed", "published", "draft", "review", "archived"})
VALID_AUDIENCES = frozenset({"beginner", "intermediate", "advanced"})
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*-\d{8}$")
URL_PATTERN = re.compile(r"^https?://")


class ValidationResult:
    """Collects validation errors for a set of files."""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.files_checked: int = 0
        self.entries_checked: int = 0
        self.files_failed: int = 0
        self.entries_failed: int = 0

    def add_error(self, file_path: str, entry_id: str | None, message: str) -> None:
        location = f"{file_path}"
        if entry_id:
            location += f"[id={entry_id}]"
        self.errors.append(f"  ✗ {location}: {message}")

    def summary(self) -> str:
        lines = [
            f"  Files checked: {self.files_checked}",
            f"  Entries checked: {self.entries_checked}",
            f"  Entries failed: {self.entries_failed}",
            f"  Files with errors: {self.files_failed}",
            f"  Total errors: {len(self.errors)}",
        ]
        return "\n".join(lines)

    @property
    def passed(self) -> bool:
        return self.files_failed == 0 and self.entries_failed == 0


def validate_required_fields(
    entry: dict[str, Any], file_path: str, entry_id: str | None, result: ValidationResult
) -> None:
    """Check required fields exist and have correct types."""
    for field, expected_type in REQUIRED_FIELDS.items():
        if field not in entry:
            result.add_error(
                file_path, entry_id,
                f"Missing required field: '{field}'",
            )
            continue
        value = entry[field]
        if not isinstance(value, expected_type):
            result.add_error(
                file_path, entry_id,
                f"Field '{field}' should be {expected_type.__name__}, "
                f"got {type(value).__name__}",
            )


def validate_id(entry: dict[str, Any], file_path: str, result: ValidationResult) -> str | None:
    """Validate id field format and return the id value (or None)."""
    entry_id = entry.get("id")
    if entry_id is None:
        return None
    if not isinstance(entry_id, str):
        return str(entry_id)
    if not ID_PATTERN.match(entry_id):
        result.add_error(
            file_path, entry_id,
            f"Invalid id format: '{entry_id}' "
            f"(expected {{slug}}-{{YYYYMMDD}}, e.g. my-article-20260317)",
        )
    return entry_id


def validate_status(entry: dict[str, Any], file_path: str, entry_id: str | None, result: ValidationResult) -> None:
    """Validate status field value."""
    status = entry.get("status")
    if not isinstance(status, str):
        return
    if status not in VALID_STATUSES:
        result.add_error(
            file_path, entry_id,
            f"Invalid status: '{status}' "
            f"(must be one of: {', '.join(sorted(VALID_STATUSES))})",
        )


def validate_url(entry: dict[str, Any], file_path: str, entry_id: str | None, result: ValidationResult) -> None:
    """Validate source_url field format."""
    url = entry.get("source_url")
    if not isinstance(url, str):
        return
    if not URL_PATTERN.match(url):
        result.add_error(
            file_path, entry_id,
            f"Invalid source_url: '{url}' (must start with http:// or https://)",
        )


def validate_summary(entry: dict[str, Any], file_path: str, entry_id: str | None, result: ValidationResult) -> None:
    """Validate summary minimum length."""
    summary = entry.get("summary")
    if not isinstance(summary, str):
        return
    if len(summary) < 20:
        result.add_error(
            file_path, entry_id,
            f"Summary too short ({len(summary)} chars, minimum 20)",
        )


def validate_tags(entry: dict[str, Any], file_path: str, entry_id: str | None, result: ValidationResult) -> None:
    """Validate tags minimum count."""
    tags = entry.get("tags")
    if not isinstance(tags, list):
        return
    if len(tags) < 1:
        result.add_error(
            file_path, entry_id,
            "Tags list is empty (minimum 1 tag required)",
        )


def validate_optional_score(entry: dict[str, Any], file_path: str, entry_id: str | None, result: ValidationResult) -> None:
    """Validate optional score field (1-10)."""
    score = entry.get("score")
    if score is None:
        return
    if not isinstance(score, (int, float)) or isinstance(score, bool):
        result.add_error(
            file_path, entry_id,
            f"Optional field 'score' must be a number, got {type(score).__name__}",
        )
    elif score < 1 or score > 10:
        result.add_error(
            file_path, entry_id,
            f"Optional field 'score' must be between 1 and 10, got {score}",
        )


def validate_optional_audience(entry: dict[str, Any], file_path: str, entry_id: str | None, result: ValidationResult) -> None:
    """Validate optional audience field."""
    audience = entry.get("audience")
    if audience is None:
        return
    if not isinstance(audience, str):
        result.add_error(
            file_path, entry_id,
            f"Optional field 'audience' must be a string, got {type(audience).__name__}",
        )
    elif audience not in VALID_AUDIENCES:
        result.add_error(
            file_path, entry_id,
            f"Invalid audience: '{audience}' "
            f"(must be one of: {', '.join(sorted(VALID_AUDIENCES))})",
        )


def validate_entry(entry: dict[str, Any], file_path: str, result: ValidationResult) -> None:
    """Run all validations on a single entry."""
    original_errors = len(result.errors)

    entry_id = validate_id(entry, file_path, result)
    validate_required_fields(entry, file_path, entry_id, result)
    validate_status(entry, file_path, entry_id, result)
    validate_url(entry, file_path, entry_id, result)
    validate_summary(entry, file_path, entry_id, result)
    validate_tags(entry, file_path, entry_id, result)
    validate_optional_score(entry, file_path, entry_id, result)
    validate_optional_audience(entry, file_path, entry_id, result)

    if len(result.errors) > original_errors:
        result.entries_failed += 1


def validate_file(file_path: str, result: ValidationResult) -> None:
    """Parse and validate a single JSON file."""
    path = Path(file_path)

    if not path.exists():
        result.add_error(file_path, None, "File not found")
        result.files_failed += 1
        result.files_checked += 1
        return

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        result.add_error(file_path, None, f"Invalid JSON: {exc}")
        result.files_failed += 1
        result.files_checked += 1
        return

    result.files_checked += 1

    if isinstance(data, dict):
        entries = [data]
    elif isinstance(data, list):
        entries = data
    else:
        result.add_error(file_path, None, f"Unexpected JSON root type: {type(data).__name__}")
        result.files_failed += 1
        return

    file_had_errors = False
    for entry in entries:
        if not isinstance(entry, dict):
            result.add_error(file_path, None, f"Expected JSON object, got {type(entry).__name__}")
            result.entries_checked += 1
            result.entries_failed += 1
            file_had_errors = True
            continue

        result.entries_checked += 1
        errors_before = len(result.errors)
        validate_entry(entry, file_path, result)
        if len(result.errors) > errors_before:
            file_had_errors = True

    if file_had_errors:
        result.files_failed += 1


def collect_json_files(args: list[str]) -> list[str]:
    """Resolve input arguments into a list of JSON file paths."""
    files: list[str] = []
    for arg in args:
        path = Path(arg)
        if path.is_file():
            files.append(str(path.resolve()))
        elif "*" in arg:
            matched = list(Path().glob(arg))
            if matched:
                files.extend(str(p.resolve()) for p in sorted(matched))
            else:
                files.append(arg)
        else:
            matched = list(Path().glob(arg))
            if matched:
                files.extend(str(p.resolve()) for p in sorted(matched))
            else:
                files.append(arg)
    return files


def main() -> None:
    """Entry point."""
    if len(sys.argv) < 2:
        print("Usage: python hooks/validate_json.py <json_file> [json_file2 ...]")
        sys.exit(1)

    files = collect_json_files(sys.argv[1:])
    result = ValidationResult()

    for file_path in files:
        validate_file(file_path, result)

    print(f"\n{'=' * 50}")
    print("Validation Summary")
    print(f"{'=' * 50}")
    print(result.summary())

    if result.errors:
        print(f"\nError List:")
        for error in result.errors:
            print(error)

    if result.passed:
        print("\n✓ All entries passed validation.")
        sys.exit(0)
    else:
        print(f"\n✗ Validation failed for {result.entries_failed} entries.")
        sys.exit(1)


def handle_after_save(file_paths: list[str], **kwargs: Any) -> None:
    """Hook: after_save 事件处理 — 验证已保存的 JSON 文件。

    Args:
        file_paths: 已保存的 JSON 文件路径列表。
    """
    result = ValidationResult()
    for path in file_paths:
        validate_file(path, result)
    if result.passed:
        logging.getLogger(__name__).info(
            "Hook validate_json: all %d files passed validation", len(file_paths))
    else:
        logging.getLogger(__name__).warning(
            "Hook validate_json: %d/%d files failed validation",
            result.files_failed, len(file_paths))
        for error in result.errors:
            logging.getLogger(__name__).warning("  %s", error)


if __name__ == "__main__":
    main()
