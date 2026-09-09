#!/usr/bin/env python3
"""Compile declarative URL redirects into Apache configuration artifacts."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml


BEGIN_MARKER = "# BEGIN GENERATED REDIRECTS"
END_MARKER = "# END GENERATED REDIRECTS"
MAP_NAME = "acl_redirects"
ALLOWED_MATCH_TYPES = {"exact", "prefix", "regex"}
ALLOWED_REDIRECT_STATUSES = {301, 302, 303, 307, 308, 410}
ALLOWED_QUERY_POLICIES = {"preserve", "discard", "replace", "append"}
ALLOWED_ENTRY_KEYS = {
    "case_sensitive",
    "direct",
    "from",
    "match",
    "note",
    "query",
    "status",
    "tests",
    "to",
}
ALLOWED_BATCH_KEYS = {"added", "issues", "redirects"}
APACHE_BACKREFERENCE = re.compile(r"\$([1-9])")


class RedirectConfigError(ValueError):
    """Raised when the redirect registry cannot be compiled safely."""


@dataclass(frozen=True)
class RedirectExample:
    source: str
    target: str | None


@dataclass(frozen=True)
class Redirect:
    added: date
    issues: tuple[int, ...]
    source: str
    target: str | None
    match: str
    status: int
    query: str
    case_sensitive: bool
    direct: bool
    note: str | None
    tests: tuple[RedirectExample, ...]

    @property
    def map_eligible(self) -> bool:
        return (
            self.match == "exact"
            and self.status == 301
            and self.query == "preserve"
            and self.case_sensitive
            and not self.direct
        )


def _require_string(value: Any, field: str, entry_number: int) -> str:
    if not isinstance(value, str) or not value:
        raise RedirectConfigError(
            f"redirect {entry_number}: {field!r} must be a non-empty string"
        )
    if any(character.isspace() for character in value):
        raise RedirectConfigError(
            f"redirect {entry_number}: {field!r} must not contain whitespace"
        )
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise RedirectConfigError(
            f"redirect {entry_number}: {field!r} must not contain control characters"
        )
    return value


def _validate_source(source: str, match: str, entry_number: int) -> None:
    if match == "regex":
        if not source.startswith("^/") or not source.endswith("$"):
            raise RedirectConfigError(
                f"redirect {entry_number}: regex sources must start with '^/' and end with '$'"
            )
        try:
            re.compile(source)
        except re.error as error:
            raise RedirectConfigError(
                f"redirect {entry_number}: invalid regular expression: {error}"
            ) from error
        return

    if not source.startswith("/") or source.startswith("//"):
        raise RedirectConfigError(
            f"redirect {entry_number}: sources must be root-relative URL paths"
        )
    if "?" in source or "#" in source:
        raise RedirectConfigError(
            f"redirect {entry_number}: sources must not contain a query or fragment"
        )


def _validate_target(
    target: str | None,
    match: str,
    status: int,
    query: str,
    entry_number: int,
) -> None:
    if status == 410:
        if target is not None:
            raise RedirectConfigError(
                f"redirect {entry_number}: status 410 must not specify 'to'"
            )
        if query != "preserve":
            raise RedirectConfigError(
                f"redirect {entry_number}: status 410 does not support query handling"
            )
        return

    if target is None:
        raise RedirectConfigError(
            f"redirect {entry_number}: status {status} requires 'to'"
        )
    if target.startswith("//"):
        raise RedirectConfigError(
            f"redirect {entry_number}: protocol-relative targets are not allowed"
        )
    try:
        parsed = urlsplit(target)
    except ValueError as error:
        raise RedirectConfigError(
            f"redirect {entry_number}: target is not a valid URL"
        ) from error
    if not target.startswith("/"):
        if parsed.scheme != "https" or not parsed.netloc:
            raise RedirectConfigError(
                f"redirect {entry_number}: targets must be root-relative or HTTPS URLs"
            )
    if "#" in target:
        raise RedirectConfigError(
            f"redirect {entry_number}: targets must not contain fragments"
        )

    has_query = "?" in target
    if query in {"preserve", "discard"} and has_query:
        raise RedirectConfigError(
            f"redirect {entry_number}: query={query!r} requires a target without a query"
        )
    if query in {"replace", "append"} and not has_query:
        raise RedirectConfigError(
            f"redirect {entry_number}: query={query!r} requires a target with a query"
        )
    if match != "regex" and APACHE_BACKREFERENCE.search(target):
        raise RedirectConfigError(
            f"redirect {entry_number}: only regex targets may contain backreferences"
        )
    target_without_backreferences = APACHE_BACKREFERENCE.sub("", target)
    if any(character in target_without_backreferences for character in ("%", "$", "\\")):
        raise RedirectConfigError(
            f"redirect {entry_number}: target contains unsafe Apache expansion syntax"
        )


def _parse_examples(
    value: Any, entry_number: int, status: int
) -> tuple[RedirectExample, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise RedirectConfigError(f"redirect {entry_number}: 'tests' must be a list")

    examples = []
    for test_number, raw_example in enumerate(value, start=1):
        if not isinstance(raw_example, dict):
            raise RedirectConfigError(
                f"redirect {entry_number}, test {test_number}: expected a mapping"
            )
        allowed_keys = {"from"} if status == 410 else {"from", "to"}
        if set(raw_example) != allowed_keys:
            raise RedirectConfigError(
                f"redirect {entry_number}, test {test_number}: expected keys {sorted(allowed_keys)}"
            )
        source = _require_string(raw_example["from"], "tests.from", entry_number)
        target = (
            None
            if status == 410
            else _require_string(raw_example["to"], "tests.to", entry_number)
        )
        examples.append(RedirectExample(source, target))
    return tuple(examples)


def _parse_redirect(
    raw: Any, entry_number: int, added: date, issues: tuple[int, ...]
) -> Redirect:
    if not isinstance(raw, dict):
        raise RedirectConfigError(f"redirect {entry_number}: expected a mapping")
    unknown_keys = set(raw) - ALLOWED_ENTRY_KEYS
    if unknown_keys:
        raise RedirectConfigError(
            f"redirect {entry_number}: unknown keys: {', '.join(sorted(unknown_keys))}"
        )

    match = raw.get("match", "exact")
    if not isinstance(match, str) or match not in ALLOWED_MATCH_TYPES:
        raise RedirectConfigError(
            f"redirect {entry_number}: match must be one of {sorted(ALLOWED_MATCH_TYPES)}"
        )
    source = _require_string(raw.get("from"), "from", entry_number)
    _validate_source(source, match, entry_number)

    status = raw.get("status", 301)
    if (
        isinstance(status, bool)
        or not isinstance(status, int)
        or status not in ALLOWED_REDIRECT_STATUSES
    ):
        raise RedirectConfigError(
            f"redirect {entry_number}: status must be one of {sorted(ALLOWED_REDIRECT_STATUSES)}"
        )
    query = raw.get("query", "preserve")
    if not isinstance(query, str) or query not in ALLOWED_QUERY_POLICIES:
        raise RedirectConfigError(
            f"redirect {entry_number}: query must be one of {sorted(ALLOWED_QUERY_POLICIES)}"
        )
    case_sensitive = raw.get("case_sensitive", True)
    if not isinstance(case_sensitive, bool):
        raise RedirectConfigError(
            f"redirect {entry_number}: case_sensitive must be a boolean"
        )
    direct = raw.get("direct", False)
    if not isinstance(direct, bool):
        raise RedirectConfigError(f"redirect {entry_number}: direct must be a boolean")
    if direct and not source.startswith(("/anthology-files/", "^/anthology-files/")):
        raise RedirectConfigError(
            f"redirect {entry_number}: direct redirects must match anthology-files"
        )

    target_value = raw.get("to")
    target = (
        None
        if target_value is None
        else _require_string(target_value, "to", entry_number)
    )
    _validate_target(target, match, status, query, entry_number)

    note_value = raw.get("note")
    note = None
    if note_value is not None:
        if not isinstance(note_value, str) or not note_value.strip():
            raise RedirectConfigError(
                f"redirect {entry_number}: note must be a non-empty string"
            )
        if "\n" in note_value or "\r" in note_value:
            raise RedirectConfigError(
                f"redirect {entry_number}: note must fit on one line"
            )
        note = note_value.strip()
    tests = _parse_examples(raw.get("tests"), entry_number, status)
    if match != "exact" and not tests:
        raise RedirectConfigError(
            f"redirect {entry_number}: {match} redirects require at least one test"
        )

    redirect = Redirect(
        added=added,
        issues=issues,
        source=source,
        target=target,
        match=match,
        status=status,
        query=query,
        case_sensitive=case_sensitive,
        direct=direct,
        note=note,
        tests=tests,
    )
    _validate_examples(redirect, entry_number)
    return redirect


def _python_replacement(target: str) -> str:
    return APACHE_BACKREFERENCE.sub(lambda match: rf"\g<{match.group(1)}>", target)


def _append_path_suffix(target: str, suffix: str) -> str:
    path, separator, query = target.partition("?")
    return f"{path}{suffix}{separator}{query}"


def apply_redirect(redirect: Redirect, source: str) -> str | None:
    """Return the unqualified target for SOURCE, or None when it does not match."""
    comparison_source = source if redirect.case_sensitive else source.casefold()
    configured_source = (
        redirect.source if redirect.case_sensitive else redirect.source.casefold()
    )

    if redirect.match == "exact":
        matched = comparison_source == configured_source
        if not matched:
            return None
        return "" if redirect.status == 410 else redirect.target
    if redirect.match == "prefix":
        if not comparison_source.startswith(configured_source):
            return None
        if redirect.status == 410:
            return ""
        assert redirect.target is not None
        return _append_path_suffix(redirect.target, source[len(redirect.source) :])

    flags = 0 if redirect.case_sensitive else re.IGNORECASE
    match = re.fullmatch(redirect.source, source, flags=flags)
    if match is None:
        return None
    if redirect.status == 410:
        return ""
    assert redirect.target is not None
    return match.expand(_python_replacement(redirect.target))


def _validate_examples(redirect: Redirect, entry_number: int) -> None:
    if redirect.match == "regex" and redirect.target is not None:
        capture_count = re.compile(redirect.source).groups
        references = [
            int(match.group(1))
            for match in APACHE_BACKREFERENCE.finditer(redirect.target)
        ]
        if references and max(references) > capture_count:
            raise RedirectConfigError(
                f"redirect {entry_number}: target references a missing capture group"
            )

    for test_number, example in enumerate(redirect.tests, start=1):
        actual = apply_redirect(redirect, example.source)
        if actual is None:
            raise RedirectConfigError(
                f"redirect {entry_number}, test {test_number}: source does not match"
            )
        if redirect.status != 410 and actual != example.target:
            raise RedirectConfigError(
                f"redirect {entry_number}, test {test_number}: expected {example.target!r}, got {actual!r}"
            )


def load_redirects(config_path: Path) -> list[Redirect]:
    try:
        raw_config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise RedirectConfigError(f"invalid YAML: {error}") from error
    if not isinstance(raw_config, dict):
        raise RedirectConfigError("redirect configuration must be a mapping")
    if set(raw_config) != {"version", "batches"}:
        raise RedirectConfigError("redirect configuration requires version and batches")
    if isinstance(raw_config["version"], bool) or raw_config["version"] != 1:
        raise RedirectConfigError("unsupported redirect configuration version")
    if not isinstance(raw_config["batches"], list):
        raise RedirectConfigError("batches must be a list")

    redirects = []
    batch_dates = set()
    entry_number = 0
    for batch_number, raw_batch in enumerate(raw_config["batches"], start=1):
        if not isinstance(raw_batch, dict):
            raise RedirectConfigError(f"batch {batch_number}: expected a mapping")
        unknown_keys = set(raw_batch) - ALLOWED_BATCH_KEYS
        missing_keys = ALLOWED_BATCH_KEYS - set(raw_batch)
        if unknown_keys:
            raise RedirectConfigError(
                f"batch {batch_number}: unknown keys: {', '.join(sorted(unknown_keys))}"
            )
        if missing_keys:
            raise RedirectConfigError(
                f"batch {batch_number}: missing keys: {', '.join(sorted(missing_keys))}"
            )

        raw_added = raw_batch["added"]
        if type(raw_added) is date:
            added = raw_added
        elif isinstance(raw_added, str):
            try:
                added = date.fromisoformat(raw_added)
            except ValueError as error:
                raise RedirectConfigError(
                    f"batch {batch_number}: added must be an ISO date"
                ) from error
        else:
            raise RedirectConfigError(f"batch {batch_number}: added must be an ISO date")
        if added in batch_dates:
            raise RedirectConfigError(
                f"batch {batch_number}: duplicate added date {added.isoformat()}"
            )
        batch_dates.add(added)

        raw_issues = raw_batch["issues"]
        if not isinstance(raw_issues, list) or not raw_issues:
            raise RedirectConfigError(
                f"batch {batch_number}: issues must be a non-empty list"
            )
        if any(
            isinstance(issue, bool) or not isinstance(issue, int) or issue <= 0
            for issue in raw_issues
        ):
            raise RedirectConfigError(
                f"batch {batch_number}: issue numbers must be positive integers"
            )
        if len(raw_issues) != len(set(raw_issues)):
            raise RedirectConfigError(
                f"batch {batch_number}: issue numbers must not be repeated"
            )
        issues = tuple(raw_issues)

        raw_redirects = raw_batch["redirects"]
        if not isinstance(raw_redirects, list) or not raw_redirects:
            raise RedirectConfigError(
                f"batch {batch_number}: redirects must be a non-empty list"
            )
        for raw_redirect in raw_redirects:
            entry_number += 1
            redirects.append(_parse_redirect(raw_redirect, entry_number, added, issues))
    exact_sources = [
        redirect.source for redirect in redirects if redirect.match == "exact"
    ]
    duplicates = sorted(
        source for source in set(exact_sources) if exact_sources.count(source) > 1
    )
    if duplicates:
        raise RedirectConfigError(
            f"duplicate exact redirect sources: {', '.join(duplicates)}"
        )

    for redirect in redirects:
        if redirect.match == "exact" and redirect.target == redirect.source:
            raise RedirectConfigError(f"self-redirect at {redirect.source!r}")

    for redirect in redirects:
        candidate_targets = (
            [redirect.target]
            if redirect.match == "exact"
            else [example.target for example in redirect.tests]
        )
        for target in candidate_targets:
            if target is None or not target.startswith("/"):
                continue
            target_path = urlsplit(target).path
            for possible_next_redirect in redirects:
                if apply_redirect(possible_next_redirect, target_path) is not None:
                    raise RedirectConfigError(
                        f"redirect chain: target {target!r} starts another redirect"
                    )
    return redirects


def _qualified_target(target: str, base_url: str) -> str:
    return f"{base_url}{target}" if target.startswith("/") else target


def _apache_pattern(redirect: Redirect) -> str:
    if redirect.match == "regex":
        return f"^{redirect.source[2:]}"
    source = re.escape(redirect.source.removeprefix("/"))
    if redirect.match == "prefix":
        return f"^{source}(.*)$"
    return f"^{source}$"


def _apache_target(redirect: Redirect, base_url: str) -> str:
    assert redirect.target is not None
    target = redirect.target
    if redirect.match == "prefix":
        target = _append_path_suffix(target, "$1")
    return _qualified_target(target, base_url)


def _direct_request_condition(base_url: str, case_sensitive: bool) -> str:
    base_path = urlsplit(base_url).path.rstrip("/")
    pattern = rf"\s+{re.escape(base_path)}/anthology-files/"
    flags = " [NC]" if not case_sensitive else ""
    return f"RewriteCond %{{THE_REQUEST}} {pattern}{flags}"


def _entry_comment(redirect: Redirect) -> str:
    issue_label = "issue" if len(redirect.issues) == 1 else "issues"
    details = [
        f"added {redirect.added.isoformat()}",
        f"{issue_label} {', '.join(str(issue) for issue in redirect.issues)}",
    ]
    if redirect.note is not None:
        details.append(redirect.note)
    return "; ".join(details)


def render_map(redirects: list[Redirect], base_url: str) -> str:
    lines = ["# Generated by bin/build_redirects.py; do not edit."]
    for redirect in sorted(
        (entry for entry in redirects if entry.map_eligible),
        key=lambda entry: entry.source,
    ):
        assert redirect.target is not None
        lines.append(f"# {_entry_comment(redirect)}")
        lines.append(f"{redirect.source} {_qualified_target(redirect.target, base_url)}")
    return "\n".join(lines) + "\n"


def render_htaccess_block(
    redirects: list[Redirect], base_url: str, use_rewrite_map: bool
) -> str:
    lines = [
        BEGIN_MARKER,
        "# Generated by bin/build_redirects.py; edit hugo/redirects.yaml instead.",
    ]
    if use_rewrite_map:
        lines.extend(
            [
                "# acl_redirects must be declared with RewriteMap in server or virtual-host configuration.",
                f"RewriteCond ${{{MAP_NAME}:%{{REQUEST_URI}}|NOT_FOUND}} ^(https://.+)$",
                "RewriteRule ^ %1 [R=301,END]",
            ]
        )

    ordered_redirects = sorted(
        redirects, key=lambda redirect: 0 if redirect.match == "exact" else 1
    )
    for redirect in ordered_redirects:
        if use_rewrite_map and redirect.map_eligible:
            continue
        lines.append("")
        lines.append(f"# {_entry_comment(redirect)}")
        if redirect.direct:
            lines.append(_direct_request_condition(base_url, redirect.case_sensitive))
        pattern = _apache_pattern(redirect)
        if redirect.status == 410:
            flags = ["G"]
            if not redirect.case_sensitive:
                flags.append("NC")
            lines.append(f"RewriteRule {pattern} - [{','.join(flags)}]")
            continue

        flags = [f"R={redirect.status}", "END"]
        if redirect.query == "discard":
            flags.append("QSD")
        elif redirect.query == "append":
            flags.append("QSA")
        if not redirect.case_sensitive:
            flags.append("NC")
        lines.append(
            f"RewriteRule {pattern} {_apache_target(redirect, base_url)} [{','.join(flags)}]"
        )

    lines.extend([END_MARKER, ""])
    return "\n".join(lines)


def inject_htaccess(template: str, generated_block: str) -> str:
    if template.count(BEGIN_MARKER) != 1 or template.count(END_MARKER) != 1:
        raise RedirectConfigError(
            "htaccess template must contain exactly one generated redirect marker pair"
        )
    start = template.index(BEGIN_MARKER)
    end = template.index(END_MARKER, start) + len(END_MARKER)
    return template[:start] + generated_block.rstrip("\n") + template[end:]


def build_redirects(
    config_path: Path,
    htaccess_template_path: Path,
    htaccess_output_path: Path,
    map_output_path: Path,
    base_url: str,
    use_rewrite_map: bool,
) -> None:
    base_url = base_url.rstrip("/")
    parsed_base_url = urlsplit(base_url)
    if parsed_base_url.scheme not in {"http", "https"} or not parsed_base_url.netloc:
        raise RedirectConfigError("base URL must be an absolute HTTP(S) URL")
    if parsed_base_url.query or parsed_base_url.fragment:
        raise RedirectConfigError("base URL must not contain a query or fragment")
    if use_rewrite_map and parsed_base_url.scheme != "https":
        raise RedirectConfigError("RewriteMap targets require an HTTPS base URL")

    redirects = load_redirects(config_path)
    generated_block = render_htaccess_block(redirects, base_url, use_rewrite_map)
    template = htaccess_template_path.read_text(encoding="utf-8")
    rendered_htaccess = inject_htaccess(template, generated_block)

    htaccess_output_path.parent.mkdir(parents=True, exist_ok=True)
    map_output_path.parent.mkdir(parents=True, exist_ok=True)
    htaccess_output_path.write_text(rendered_htaccess, encoding="utf-8")
    map_output_path.write_text(render_map(redirects, base_url), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--htaccess-template", type=Path, required=True)
    parser.add_argument("--htaccess-output", type=Path, required=True)
    parser.add_argument("--map-output", type=Path, required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--use-rewrite-map", action="store_true")
    args = parser.parse_args()

    try:
        build_redirects(
            config_path=args.config,
            htaccess_template_path=args.htaccess_template,
            htaccess_output_path=args.htaccess_output,
            map_output_path=args.map_output,
            base_url=args.base_url,
            use_rewrite_map=args.use_rewrite_map,
        )
    except RedirectConfigError as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
