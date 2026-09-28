"""Static TeX/reference/resource checks; a PDF build is still needed for layout."""

import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def uncomment(text):
    return re.sub(r"(?<!\\)%[^\n]*", "", text)


def check_braces(text, name, errors):
    depth = 0
    for token in re.findall(r"\\.|[{}]", text):
        if token == "{":
            depth += 1
        elif token == "}":
            depth -= 1
        if depth < 0:
            errors.append(f"{name}: unmatched closing brace")
            return
    if depth:
        errors.append(f"{name}: {depth} unclosed braces")


def table_row_inputs(text):
    """Find includes whose file hooks would execute inside a table alignment."""
    stack, unsafe = [], []
    for token in re.finditer(r"\\(?:(begin|end)\{([^}]+)\}|input\{([^}]+)\})", uncomment(text)):
        kind, env, source = token.groups()
        if source is not None:
            if any(item in ("tabular", "tabularx", "tabular*") for item in stack):
                unsafe.append(source)
        elif kind == "begin":
            stack.append(env)
        elif stack:
            stack.pop()
    return unsafe


def main():
    errors = []
    files = {p: uncomment(p.read_text()) for p in ROOT.rglob("*.tex") if ".git" not in p.parts}
    bib = (ROOT / "references.bib").read_text()
    keys = Counter(re.findall(r"^@\w+\s*\{\s*([^,]+),", bib, re.M))
    labels = Counter(label for text in files.values() for label in re.findall(r"\\label\{([^}]+)\}", text))
    for kind, values in (("label", labels), ("bibliography key", keys)):
        errors.extend(f"Duplicate {kind}: {value}" for value, count in values.items() if count != 1)
    check_braces(bib, "references.bib", errors)
    for path, text in files.items():
        name = str(path.relative_to(ROOT))
        check_braces(text, name, errors)
        stack = []
        for kind, env in re.findall(r"\\(begin|end)\{([^}]+)\}", text):
            if kind == "begin":
                stack.append(env)
            elif not stack or stack.pop() != env:
                errors.append(f"{name}: mismatched environment {env}")
        if stack:
            errors.append(f"{name}: unclosed environments {stack}")
        errors.extend(f"{name}: include complete table outside tabular: {source}"
                      for source in table_row_inputs(text))
        if len(re.findall(r"(?<!\\)\$", text)) % 2:
            errors.append(f"{name}: odd inline-math delimiter count")
        if text.count(r"\[") != text.count(r"\]"):
            errors.append(f"{name}: unmatched display-math delimiters")
        for ref in re.findall(r"\\(?:ref|pageref|eqref|autoref)\{([^}]+)\}", text):
            if ref not in labels:
                errors.append(f"{name}: undefined reference {ref}")
        for group in re.findall(r"\\(?:cite|parencite|textcite|autocite)\*?(?:\[[^\]]*\])*\{([^}]+)\}", text):
            for key in group.split(","):
                if key.strip() not in keys:
                    errors.append(f"{name}: undefined citation {key}")
        for source in re.findall(r"\\input\{([^}]+)\}", text):
            target = ROOT / source
            if not target.suffix:
                target = target.with_suffix(".tex")
            if not target.is_file():
                errors.append(f"{name}: missing input {source}")
        for source in re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", text):
            target = ROOT / source
            if not target.is_file():
                errors.append(f"{name}: missing project-root-relative figure {source}")
        # Expand complete generated tables before checking their cell counts.
        expanded = re.sub(r"\\input\{(data/[^}]+\.tex)\}",
                          lambda m: files.get(ROOT / m[1], ""), text)
        for spec, body in re.findall(r"\\begin\{tabularx?\}(?:\{\\textwidth\})?\{([^}]+)\}(.*?)\\end\{tabularx?\}", expanded, re.S):
            columns = sum(char in "lcrXY" for char in spec)
            for row in body.split(r"\\"):
                if "&" in row and len(re.findall(r"(?<!\\)&", row)) != columns - 1:
                    errors.append(f"{name}: table cell count disagrees with {spec}")
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"PASS: {len(files)} TeX files; braces, environments, math delimiters, citations, references, inputs, figures, and table cells.")
    print("PDF compilation remains necessary to validate typesetting and layout.")


if __name__ == "__main__":
    main()
