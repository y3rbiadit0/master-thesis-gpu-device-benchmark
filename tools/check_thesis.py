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


ACRONYM_LIST = "backmatter/acronyms"
# Names and units shaped like acronyms that are deliberately not expanded.
NOT_ACRONYMS = {
    "AllReduce", "AMD", "BullSequana", "CINECA", "ConnectX", "cuBLAS", "cuSOLVERMp", "cuSPARSE",
    "DeepEP", "DGX", "DragonFly+", "GB", "GB200", "GHz", "GiB", "GPUDirect", "GPUNetIO", "HBM2e",
    "InfiniBand", "KiB", "LLVM", "LogGP", "LogP", "LUMI", "METIS", "MHz", "MiB", "MPICH",
    "MT4123", "NVIDIA", "oneAPI", "NVLink", "NVSHMEM", "NVSwitch", "OpenSHMEM", "OSHMPI", "PICO", "ROCm", "rocSHMEM",
    "SuiteSparse", "SXM", "SXM4", "SYCL", "T3D", "TOP500", "TuCCL", "vLLM", "xCCL",
}
# Product names whose parts would otherwise read as uses of a defined acronym.
COMPOUND_NAMES = ("HPC-X", r"ROC\_SHMEM", r"MLNX\_OFED", "GPU-IB")
HEADING = r"\\(?:chapter|section|subsection|subsubsection|paragraph|frontchapter)\*?\{((?:[^{}]|\{[^{}]*\})*)\}"


def acronym_definitions(text):
    """Map each \\acro key to its printed short form."""
    return {key: short or key for key, short in re.findall(r"\\acro\{([^}]+)\}(?:\[([^\]]*)\])?", uncomment(text))}


def strip_non_prose(text):
    text = uncomment(text)
    for name in COMPOUND_NAMES:
        text = text.replace(name, " ")
    text = re.sub(r"\\texttt\{(?:[^{}]|\{[^{}]*\})*\}", " ", text)
    text = re.sub(r"\\\[.*?\\\]|\$[^$]*\$", " ", text, flags=re.S)
    text = re.sub(r"\\(?:label|ref|pageref|eqref|autoref|cite|parencite|textcite|input|includegraphics)"
                  r"\*?(?:\[[^\]]*\])?\{[^}]*\}", " ", text)
    text = re.sub(r"\\begin\{tabularx?\}(?:\{\\textwidth\})?\{[^}]*\}", " ", text)
    return re.sub(r"\\(?:begin|end)\{[^}]*\}", " ", text)


def acronym_errors(scopes, definitions):
    """Check that each acronym's first prose use in every scope is its \\ac definition.

    `scopes` is a list of [(name, text)] in reading order; \\acresetall separates them.
    Headings are excluded from the order (they feed the table of contents) but are
    still checked for unlisted acronyms.
    """
    errors, used = [], set()
    by_short = {short: key for key, short in definitions.items()}

    def lookup(word):
        for form in (word, word[:-1] if word.endswith("s") else None, re.sub(r"\d+$", "", word)):
            if form in by_short:
                return by_short[form]
        return None

    def unlisted(word):
        return sum(c.isupper() for c in word) >= 2 and word not in NOT_ACRONYMS and lookup(word) is None

    for scope in scopes:
        defined, reported = set(), set()
        for name, raw in scope:
            text = strip_non_prose(raw)
            for heading in re.findall(HEADING, text):
                errors.extend(f"{name}: unlisted acronym {word} in heading"
                              for word in re.findall(r"[A-Za-z][A-Za-z0-9+]*", heading) if unlisted(word))
            text = re.sub(HEADING, " ", text)
            for match in re.finditer(r"\(([A-Za-z][A-Za-z0-9+]*)\)", text):
                if lookup(match[1]):
                    errors.append(f"{name}: hand-written expansion ({match[1]}); use \\ac{{{lookup(match[1])}}}")
            for match in re.finditer(r"\\ac[pl]?\{([^}]+)\}|\\[A-Za-z@]+|([A-Za-z][A-Za-z0-9+]*)", text):
                key, word = match[1], match[2]
                if key:
                    if key not in definitions:
                        errors.append(f"{name}: \\ac of unlisted acronym {key}")
                    elif key in defined:
                        errors.append(f"{name}: {key} defined again; use plain text after the first \\ac")
                    defined.add(key)
                    used.add(key)
                elif word and lookup(word):
                    if lookup(word) not in defined and lookup(word) not in reported:
                        errors.append(f"{name}: {word} used before its \\ac definition")
                        reported.add(lookup(word))
                elif word and unlisted(word) and word not in reported:
                    errors.append(f"{name}: unlisted acronym {word}")
                    reported.add(word)
    errors.extend(f"{ACRONYM_LIST}.tex: {key} is never used" for key in definitions if key not in used)
    return errors


def acronym_scopes(files):
    """Split main.tex's inputs into reading-order scopes at each \\acresetall."""
    scopes = [[]]
    main_text = uncomment((ROOT / "main.tex").read_text())
    for reset, source in re.findall(r"(\\acresetall)|\\input\{([^}]+)\}", main_text):
        if reset:
            scopes.append([])
        elif source != ACRONYM_LIST:
            path = ROOT / (source if source.endswith(".tex") else source + ".tex")
            scopes[-1].append((source, files.get(path, "")))
    return scopes


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
    definitions = acronym_definitions(files.get(ROOT / f"{ACRONYM_LIST}.tex", ""))
    errors.extend(acronym_errors(acronym_scopes(files), definitions))
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"PASS: {len(files)} TeX files; braces, environments, math delimiters, citations, references, inputs, figures, table cells, and acronyms.")
    print("PDF compilation remains necessary to validate typesetting and layout.")


if __name__ == "__main__":
    main()
