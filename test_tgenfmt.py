# SPDX-License-Identifier: Apache-2.0
"""Tests for tgenfmt.py."""

from __future__ import annotations

import textwrap
from pathlib import Path

from tgenfmt import format_text, process_file


def _dedent(text: str) -> str:
    return textwrap.dedent(text)


def test_normalizes_safe_tablegen_spacing() -> None:
    assert format_text('include   "mlir/IR/OpBase.td"   \n') == 'include "mlir/IR/OpBase.td"\n'
    assert format_text("foreach kind=[\"a\"] in {  \n") == 'foreach kind = ["a"] in {\n'


def test_preserves_let_and_defvar_alignment() -> None:
    source = _dedent(
        """\
        defvar Short     = 1;
        defvar LongerOne = 2;
          let Pattern     = [];
          let Constraints = cstr;
        """
    )
    assert format_text(source) == source


def test_wraps_long_arguments_dag() -> None:
    source = (
        "  let arguments = (ins VeryLongTypeName:$first, "
        "AnotherVeryLongTypeName:$second, ThirdVeryLongTypeName:$third);\n"
    )
    assert format_text(source, line_width=80) == (
        "  let arguments = (ins\n"
        "    VeryLongTypeName:$first,\n"
        "    AnotherVeryLongTypeName:$second,\n"
        "    ThirdVeryLongTypeName:$third\n"
        "  );\n"
    )


def test_wraps_long_results_dag() -> None:
    source = "  let results = (outs VeryLongTypeName:$first, AnotherVeryLongTypeName:$second);\n"
    assert format_text(source, line_width=60) == (
        "  let results = (outs\n"
        "    VeryLongTypeName:$first,\n"
        "    AnotherVeryLongTypeName:$second\n"
        "  );\n"
    )


def test_preserves_short_dag() -> None:
    source = "  let results = (outs AnyType:$result);\n"
    assert format_text(source) == source


def test_wraps_long_header_trait_list() -> None:
    source = (
        'def GPU_CreateDnTensorOp : GPU_Op<"create_dn_tensor", '
        "[GPU_AsyncOpInterface, AttrSizedOperandSegments]> {\n"
    )
    assert format_text(source, line_width=80) == (
        'def GPU_CreateDnTensorOp : GPU_Op<"create_dn_tensor", [\n'
        "  GPU_AsyncOpInterface,\n"
        "  AttrSizedOperandSegments\n"
        "]> {\n"
    )


def test_preserves_short_header_trait_list() -> None:
    source = 'def FooOp : Foo_Op<"foo", [Pure]> {\n'
    assert format_text(source, line_width=80) == source


def test_does_not_wrap_first_template_argument_list() -> None:
    source = 'def AnyIntegerOrFloat : AnyTypeOf<[AnySignlessInteger, AnyFloat], "Integer or Float">;\n'
    assert format_text(source, line_width=40) == source


def test_does_not_wrap_non_final_template_argument_list() -> None:
    source = "def MOPPredicate : ScalableVectorOfRankAndLengthAndType<[1], [16, 8, 4, 2], [I1]> {\n"
    assert format_text(source, line_width=40) == source


def test_preserves_token_pasted_header() -> None:
    source = 'def NAME # Foo : Foo_Op<"foo", [Pure, AttrSizedOperandSegments]> {\n'
    assert format_text(source, line_width=20) == source


def test_preserves_empty_file() -> None:
    assert format_text("") == ""


def test_preserves_opaque_blocks() -> None:
    source = _dedent(
        """\
        def SomeOp : Op<SomeDialect, "some.op"> {
          let description = [{
            This line keeps   its spacing.
              So does this one.
          }];
          let   summary   =   "x";
        }
        """
    )
    assert format_text(source) == source


def test_respects_off_on_guards() -> None:
    source = _dedent(
        """\
        // tgenfmt: off
        include   "mlir/IR/OpBase.td"
        // tgenfmt: on
        include   "mlir/IR/BuiltinTypes.td"
        """
    )
    assert format_text(source) == _dedent(
        """\
        // tgenfmt: off
        include   "mlir/IR/OpBase.td"
        // tgenfmt: on
        include "mlir/IR/BuiltinTypes.td"
        """
    )


def test_check_mode_does_not_write(tmp_path: Path) -> None:
    path = tmp_path / "Ops.td"
    path.write_text('include   "mlir/IR/OpBase.td"\n')

    assert process_file(path, check=True)
    assert path.read_text() == 'include   "mlir/IR/OpBase.td"\n'


def test_process_file_writes_changes(tmp_path: Path) -> None:
    path = tmp_path / "Ops.td"
    path.write_text('include   "mlir/IR/OpBase.td"\n')

    assert process_file(path)
    assert path.read_text() == 'include "mlir/IR/OpBase.td"\n'
