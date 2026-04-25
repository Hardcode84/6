# MLIR TableGen Formatting Notes

This document captures common formatting conventions observed in the MLIR
TableGen corpus, especially under `mlir/include/mlir`. It is intended as a
target style guide for a TableGen formatter, not as a full TableGen language
reference.

## Scope

The surveyed corpus covers MLIR `.td` files across core IR, dialects,
interfaces, passes, transforms, conversion, rewrite utilities, bytecode, and
LLVMIR target interfaces.

The important conclusion is that MLIR TableGen style is structured but not
uniform. A useful formatter should be conservative, preserve local density, and
avoid reflowing semantically fragile constructs.

## File Structure

Most files use the LLVM source banner, a license block, and include guards:

```tablegen
//===-- File.td - Short title ------------------------------*- tablegen -*-===//
//
// Part of the LLVM Project, under the Apache License v2.0 with LLVM Exceptions.
// See https://llvm.org/LICENSE.txt for license information.
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
//
//===----------------------------------------------------------------------===//
//
// Short description.
//
//===----------------------------------------------------------------------===//

#ifndef SOME_GUARD
#define SOME_GUARD

include "mlir/..."

#endif // SOME_GUARD
```

Formatter policy:

- Preserve an existing banner, abstract block, include guard, and closing guard
  comment.
- Do not synthesize banners or guards for files that omit them.
- Keep `include "mlir/..."` one per line.
- Preserve blank lines between include groups.
- Preserve section dividers such as `//===----------------------------------------------------------------------===//`
  and shorter variants.
- Preserve dialect-specific thin separators such as `// -----`.

## Indentation

Common indentation is two spaces for nested TableGen constructs:

```tablegen
def SomeOp : Op<...> {
  let summary = "...";
  let arguments = (ins
    AnyType:$value
  );
}
```

Formatter policy:

- Use two spaces for record bodies and nested blocks.
- Preserve the file's existing continuation style for inheritance where
  practical. MLIR commonly uses both two-space and four-space continuations.
- Do not enforce strict vertical column alignment.

## Line Width

Use an 80-column target, but treat it as a soft preference rather than a hard
limit. MLIR TableGen contains many constructs where forced wrapping is worse
than overflow.

Formatter policy:

- Prefer wrapping safe syntactic structures before they exceed 80 columns.
- Safe structures include long inheritance lists, template parameter lists,
  multiline lists, and `(ins ...)` / `(outs ...)` DAGs.
- Allow overflow for opaque or fragile constructs such as `[{ ... }]`, string
  literals, `CPred`, C++ code blocks, `assemblyFormat`, token-pasted names using
  `#`, and compact records that are intentionally tabular.
- Do not reflow a line solely to satisfy the 80-column target when doing so
  would reduce readability or risk changing semantics.

## Includes

Includes are lowercase TableGen includes with quoted paths:

```tablegen
include "mlir/IR/OpBase.td"
include "mlir/Interfaces/SideEffectInterfaces.td"

include "mlir/Dialect/SomeDialect/IR/SomeBase.td"
```

Formatter policy:

- Keep one include per line.
- Preserve grouping blank lines.
- Sort consecutive include lines lexicographically within each group.
- Treat blank lines and comments as group boundaries.

## Records

MLIR uses both compact and expanded records.

Compact records are common for traits, constraints, enum cases, and small helper
defs:

```tablegen
def AffineScope : NativeOpTrait<"AffineScope">;
def SomeTrait : NativeOpTrait<"SomeTrait"> { let cppNamespace = "::mlir"; }
```

Expanded records are common when there are multiple `let` assignments, prose
blocks, builders, methods, arguments, or results:

```tablegen
def SomeOp : Op<SomeDialect, "some.op"> {
  let summary = "short summary";

  let description = [{
    Long markdown-like prose is usually kept inside this block and should not be
    reflowed by a TableGen formatter.
  }];
}
```

Formatter policy:

- Preserve one-line semicolon records.
- Preserve compact one-line brace records when they are already compact.
- Prefer expanded braces for records with multiple fields.
- Use one `let name = value;` per line inside expanded records.
- Preserve blank lines that separate logical groups inside records.

## Classes And Inheritance

Long template parameter and inheritance lists usually wrap rather than align to
hard columns.

Common style with the base after a line break:

```tablegen
class SomeOp<string mnemonic, list<Trait> traits = []> :
    Op<SomeDialect, mnemonic, traits>;
```

Common style with the closing `>` on its own line and the colon indented:

```tablegen
class SomeStructuredOp<
    string mnemonic,
    list<Trait> traits = []
  > : Op<SomeDialect, mnemonic, traits>;
```

Long ODS op headers with a final trait list may wrap the list vertically:

```tablegen
def SomeOp : SomeDialect_Op<"some.op", [
  TraitOne,
  TraitTwo
]> {
```

Formatter policy:

- Keep short class and def headers on one line when they fit.
- For long template parameter lists, put one logical parameter per line.
- For long inheritance lists, put one base per line.
- For long ODS op headers, wrap a final `[...]` trait list one trait per line.
- Preserve trailing `#` concatenation placement in existing headers.
- Avoid bouncing between two-space and four-space continuation styles inside the
  same file.

## Multiclass, Defm, Foreach, And Defvar

These constructs are less common than plain `def` and `class`, but appear in
some dialects and generated families.

```tablegen
foreach kind = ["a", "b"] in {
  defvar Name = kind # "_suffix";
  def SomePrefix # kind # Op : SomeBase<kind>;
}
```

Formatter policy:

- Format `foreach var = list in {` with a normal braced block.
- Indent generated `def`, `defm`, and `defvar` lines by two spaces.
- Do not split token-pasted names like `def A # B # C` unless already split.
- Preserve `defvar Name = [{ ... }];` bodies as opaque text.

## Let Scopes

Scoped `let` blocks are semantically important:

```tablegen
let cppNamespace = "::mlir::some_dialect" in {
  def SomeOp : SomeBase<"some.op">;
}
```

Formatter policy:

- Preserve `let name = value in {` as a block opener.
- Never merge a scoped `let ... in` line with a following `def`.
- Keep the scoped body indented by two spaces.

## DAG Expressions

MLIR uses DAG expressions heavily for operands, results, builders, methods, and
patterns.

Short DAGs may stay on one line:

```tablegen
let results = (outs AnyType:$result);
```

Long `(ins ...)` and `(outs ...)` DAGs are usually split with one field per
line:

```tablegen
let arguments = (ins
  AnyType:$lhs,
  AnyType:$rhs,
  OptionalAttr<I64Attr>:$kind
);

let results = (outs
  AnyType:$result
);
```

Formatter policy:

- Keep short DAGs on one line when they fit and are already readable.
- When breaking `(ins ...)` or `(outs ...)`, place one operand, result, or
  attribute per line.
- Use trailing commas for multiline DAG entries when the surrounding file does.
- Put the closing `);` on its own line for multiline `let arguments` and
  `let results`.
- Preserve blank lines between multiline `arguments` and `results` blocks.
- Avoid aggressive reflow of nested DAGs and unusual bytecode-style DAGs.

## Lists

MLIR often uses multiline lists for builders, methods, options, traits, and pass
configuration.

```tablegen
let builders = [
  OpBuilder<(ins "Type":$type, "Value":$value), [{
    build($_builder, $_state, type, value);
  }]>
];
```

Formatter policy:

- Preserve multiline list density.
- Preserve trailing commas in multiline lists.
- Keep complex list elements such as `InterfaceMethod`, `OpBuilder`, and pass
  options as self-contained multiline items.
- Do not reflow C++ code blocks or prose blocks inside list entries.

## Opaque Blocks

The following should be treated as opaque by default:

- `[{ ... }]` prose, assembly formats, C++ code, predicates, and method bodies.
- `code`-like fields and `CPred` expressions.
- Markdown-like descriptions.
- Multi-line strings and snippets built with `#` concatenation.

Formatter policy:

- Preserve internal whitespace inside `[{ ... }]`.
- Do not wrap, join, or indent-normalize C++ code inside TableGen code blocks
  unless an explicit mode is added later.
- Do not rewrite string concatenation boundaries.

## Comments

Common comment forms:

```tablegen
//===----------------------------------------------------------------------===//
// Section Title
//===----------------------------------------------------------------------===//

// Short explanation for the following record.
def SomeDef : SomeBase;

// -----
```

Formatter policy:

- Keep leading comments attached to the following record.
- Preserve TODO and FIXME comments in place.
- Preserve file and section divider spelling.
- Do not reflow long prose comments unless a dedicated comment formatter is
  enabled.

## Conservative Cases

A formatter should avoid changing layout around:

- `let ... in { ... }` scopes.
- Token-pasted names using `#`.
- Multiline `CPred`, `code`, and `[{ ... }]` blocks.
- Dense bytecode definitions with compact one-line bodies.
- Nested DAGs split in unusual ways.
- Files that intentionally omit the normal LLVM banner or closing guard comment.

## Initial Formatter Policy

The formatter should start as a structure-preserving formatter:

- Parse and print known TableGen syntax rather than using regex rewrites.
- Make formatting idempotent.
- Preserve comments and opaque text exactly.
- Preserve compact records where they are already compact.
- Expand only clear multiline structures such as long DAGs, long lists, and long
  inheritance lists.
- Use two-space indentation for nested TableGen blocks.
- Avoid sorting, regrouping, or semantic rewrites.

Representative files from the survey include:

- `IR/OpBase.td`
- `IR/BuiltinDialect.td`
- `IR/PatternBase.td`
- `IR/Constraints.td`
- `IR/EnumAttr.td`
- `IR/BuiltinDialectBytecode.td`
- `Interfaces/ControlFlowInterfaces.td`
- `Pass/PassBase.td`
- `Transforms/Passes.td`
- `Conversion/Passes.td`
- `Dialect/Arith/IR/ArithOps.td`
- `Dialect/Func/IR/FuncOps.td`
- `Dialect/Linalg/IR/LinalgStructuredOps.td`
- `Dialect/SPIRV/IR/SPIRVArithmeticOps.td`
- `Dialect/LLVMIR/ROCDLOps.td`
- `Dialect/LLVMIR/XeVMOps.td`
- `Dialect/SMT/IR/SMTBitVectorOps.td`
- `Target/LLVMIR/LLVMTranslationDialectInterface.td`
- `Target/LLVMIR/LLVMImportDialectInterface.td`
