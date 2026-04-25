#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Conservative formatter for LLVM TableGen files.

This formatter starts deliberately small: it normalizes whitespace in simple
TableGen syntax and expands straightforward one-line ODS argument/result DAGs
when they exceed the configured line width. It treats code/prose blocks as
opaque and supports ``// tgenfmt: off`` / ``// tgenfmt: on`` guards.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

DEFAULT_LINE_WIDTH = 80

_INCLUDE_RE = re.compile(r'^(\s*)include\s+("[^"]+")\s*$')
_FOREACH_RE = re.compile(r"^(\s*)foreach\s+(.+?)\s*=\s*(.+?)\s+in\s+\{\s*$")
_HEADER_RE = re.compile(r"^\s*(?:def|class)\s+\S+")
_SIMPLE_DAG_LET_RE = re.compile(
    r"^(\s*)let\s+(arguments|results)\s*=\s*\((ins|outs)\s+(.+)\);\s*$"
)


def _strip_trailing_whitespace(line: str) -> str:
    return line.rstrip(" \t")


def _contains_opaque_start(line: str) -> bool:
    return "[{" in line


def _contains_opaque_end(line: str) -> bool:
    return "}]" in line


def _split_top_level_commas(text: str) -> list[str] | None:
    """Split *text* on top-level commas, or return None for unsafe input."""
    parts: list[str] = []
    start = 0
    angle_depth = 0
    square_depth = 0
    paren_depth = 0
    brace_depth = 0
    in_string = False
    escaped = False

    for i, char in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "<":
            angle_depth += 1
        elif char == ">":
            angle_depth -= 1
        elif char == "[":
            square_depth += 1
        elif char == "]":
            square_depth -= 1
        elif char == "(":
            paren_depth += 1
        elif char == ")":
            paren_depth -= 1
        elif char == "{":
            brace_depth += 1
        elif char == "}":
            brace_depth -= 1
        elif (
            char == ","
            and angle_depth == 0
            and square_depth == 0
            and paren_depth == 0
            and brace_depth == 0
        ):
            parts.append(text[start:i].strip())
            start = i + 1

        if min(angle_depth, square_depth, paren_depth, brace_depth) < 0:
            return None

    if in_string or any((angle_depth, square_depth, paren_depth, brace_depth)):
        return None

    parts.append(text[start:].strip())
    if len(parts) <= 1 or any(not part for part in parts):
        return None
    return parts


def _find_square_lists(text: str) -> list[tuple[int, int]]:
    """Return square-list spans outside strings."""
    spans: list[tuple[int, int]] = []
    square_depth = 0
    start = -1
    in_string = False
    escaped = False

    for i, char in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "[":
            if square_depth == 0:
                start = i
            square_depth += 1
        elif char == "]":
            square_depth -= 1
            if square_depth < 0:
                return []
            if square_depth == 0 and start != -1:
                spans.append((start, i))
                start = -1

    return spans if square_depth == 0 and not in_string else []


def _format_simple_dag_let(line: str, *, line_width: int) -> list[str] | None:
    match = _SIMPLE_DAG_LET_RE.match(line)
    if not match or len(line) <= line_width:
        return None

    indent, name, marker, body = match.groups()
    parts = _split_top_level_commas(body)
    if parts is None:
        return None

    continuation = indent + "  "
    formatted = [f"{indent}let {name} = ({marker}"]
    formatted.extend(f"{continuation}{part}," for part in parts[:-1])
    formatted.append(f"{continuation}{parts[-1]}")
    formatted.append(f"{indent});")
    return formatted


def _format_header_square_list(line: str, *, line_width: int) -> list[str] | None:
    stripped_line = _strip_trailing_whitespace(line)
    if len(stripped_line) <= line_width or not _HEADER_RE.match(stripped_line):
        return None
    if "#" in stripped_line:
        return None

    start = end = -1
    for candidate_start, candidate_end in _find_square_lists(stripped_line):
        before = stripped_line[:candidate_start].rstrip()
        after = stripped_line[candidate_end + 1 :].lstrip()
        # ODS op traits commonly appear as Base<..., [Trait, Trait]>.
        # Avoid broad rewrites of first template-argument lists like
        # AnyTypeOf<[A, B], "description"> and non-final lists like
        # Base<[1], [2, 4], [I1]>.
        if before.endswith(",") and after.startswith(">"):
            start, end = candidate_start, candidate_end
            break
    if start == -1:
        return None

    parts = _split_top_level_commas(stripped_line[start + 1 : end])
    if parts is None:
        return None

    indent = stripped_line[: len(stripped_line) - len(stripped_line.lstrip())]
    continuation = indent + "  "
    formatted = [stripped_line[: start + 1]]
    formatted.extend(f"{continuation}{part}," for part in parts[:-1])
    formatted.append(f"{continuation}{parts[-1]}")
    formatted.append(f"{indent}]{stripped_line[end + 1:]}")
    return formatted


def _format_line(line: str, *, line_width: int) -> list[str]:
    stripped_line = _strip_trailing_whitespace(line)

    dag_lines = _format_simple_dag_let(stripped_line, line_width=line_width)
    if dag_lines is not None:
        return dag_lines

    header_lines = _format_header_square_list(stripped_line, line_width=line_width)
    if header_lines is not None:
        return header_lines

    if match := _INCLUDE_RE.match(stripped_line):
        indent, path = match.groups()
        return [f"{indent}include {path}"]

    if match := _FOREACH_RE.match(stripped_line):
        indent, name, value = match.groups()
        return [f"{indent}foreach {name} = {value} in {{"]

    return [line]


def format_text(text: str, *, line_width: int = DEFAULT_LINE_WIDTH) -> str:
    """Return formatted TableGen text."""
    if not text:
        return text

    lines = text.splitlines()
    formatted: list[str] = []
    enabled = True
    opaque_depth = 0

    for line in lines:
        stripped = line.strip()

        if stripped == "// tgenfmt: off":
            enabled = False
            formatted.append(_strip_trailing_whitespace(line))
            continue
        if stripped == "// tgenfmt: on":
            enabled = True
            formatted.append(_strip_trailing_whitespace(line))
            continue

        if not enabled or opaque_depth:
            formatted.append(line)
        elif _contains_opaque_start(line):
            formatted.append(line)
        else:
            formatted.extend(_format_line(line, line_width=line_width))

        if _contains_opaque_start(line):
            opaque_depth += line.count("[{")
        if opaque_depth and _contains_opaque_end(line):
            opaque_depth = max(0, opaque_depth - line.count("}]"))

    return "\n".join(formatted) + "\n"


def process_file(path: Path, *, check: bool = False, line_width: int = DEFAULT_LINE_WIDTH) -> bool:
    """Format one file. Return True if the file changed or would change."""
    original = path.read_text()
    formatted = format_text(original, line_width=line_width)
    changed = formatted != original
    if changed and not check:
        path.write_text(formatted)
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", type=Path, help="TableGen files to format.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if files would change, but do not modify them.",
    )
    parser.add_argument(
        "--line-width",
        type=int,
        default=DEFAULT_LINE_WIDTH,
        help=f"Soft line width target for safe rewrites. Default: {DEFAULT_LINE_WIDTH}.",
    )
    args = parser.parse_args()

    failed: list[Path] = []
    for path in args.files:
        if not path.exists():
            print(f"tgenfmt: {path}: no such file", file=sys.stderr)
            failed.append(path)
            continue
        if process_file(path, check=args.check, line_width=args.line_width):
            failed.append(path)
            if args.check:
                print(f"would reformat {path}", file=sys.stderr)
            else:
                print(f"reformatted {path}", file=sys.stderr)

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
