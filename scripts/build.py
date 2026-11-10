#!/usr/bin/env python3
"""Build pipeline for the AI Tools knowledge graph.

Steps:
  1. parse ontology, data and shapes (Turtle syntax check)
  2. ontology documentation check (every class/property has rdfs:label + rdfs:comment)
  3. OWL 2 RL reasoning + consistency check (disjointness, irreflexivity, functionality)
  4. dataset statistics
  5. run all SPARQL queries in queries/ and store results (Markdown + CSV / Turtle)
  6. SHACL validation of the valid data and of valid + intentionally invalid data
  7. generate the conceptual-model diagram (Graphviz)
  8. assemble the report (report/report.md -> build/report.md)

Usage: python scripts/build.py
"""
from __future__ import annotations

import csv
import io
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import owlrl
from pyshacl import validate
from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.collection import Collection
from rdflib.namespace import OWL, RDF, RDFS, XSD

ROOT = Path(__file__).resolve().parent.parent
ONTO = ROOT / "ontology" / "ai-tools.ttl"
DATA = ROOT / "data" / "ai-tools-data.ttl"
INVALID = ROOT / "data" / "ai-tools-data-invalid.ttl"
SHAPES = ROOT / "shacl" / "shapes.ttl"
QUERIES = ROOT / "queries"
RESULTS = ROOT / "results"
BUILD = ROOT / "build"
FIGURES = ROOT / "report" / "figures"

AIT = Namespace("https://otavlna.github.io/4iz444-ai-tools-kg/ontology#")
AID = Namespace("https://otavlna.github.io/4iz444-ai-tools-kg/data/")
SH = Namespace("http://www.w3.org/ns/shacl#")

PREFIXES = {
    str(AIT): "ait:",
    str(AID): "aid:",
    str(XSD): "xsd:",
    str(RDFS): "rdfs:",
    "https://schema.org/": "schema:",
}

errors: list[str] = []


def log(msg: str) -> None:
    print(msg, flush=True)


def short(term) -> str:
    if term is None:
        return ""
    if isinstance(term, Literal):
        return str(term)
    s = str(term)
    for ns, p in PREFIXES.items():
        if s.startswith(ns):
            return p + s[len(ns):]
    return s


def parse(path: Path) -> Graph:
    g = Graph()
    g.parse(path, format="turtle")
    log(f"  parsed {path.relative_to(ROOT)}: {len(g)} triples")
    return g


# --------------------------------------------------------------------------- 2
def check_documentation(onto: Graph) -> list[str]:
    missing = []
    kinds = [OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty]
    for kind in kinds:
        for s in onto.subjects(RDF.type, kind):
            if not isinstance(s, URIRef) or not str(s).startswith(str(AIT)):
                continue
            for p in (RDFS.label, RDFS.comment):
                if (s, p, None) not in onto:
                    missing.append(f"{short(s)} lacks {short(p)}")
    return missing


# --------------------------------------------------------------------------- 3
def disjoint_pairs(g: Graph) -> set[tuple]:
    pairs = set()
    for a, b in g.subject_objects(OWL.disjointWith):
        pairs.add((a, b))
    for adc in g.subjects(RDF.type, OWL.AllDisjointClasses):
        members = list(Collection(g, g.value(adc, OWL.members)))
        for i, a in enumerate(members):
            for b in members[i + 1:]:
                pairs.add((a, b))
    return pairs


def consistency_check(onto: Graph, data: Graph) -> tuple[list[str], int]:
    g = Graph()
    g += onto
    g += data
    before = len(g)
    owlrl.DeductiveClosure(owlrl.OWLRL_Semantics, axiomatic_triples=False,
                           datatype_axioms=False).expand(g)
    inferred = len(g) - before
    problems = []
    for a, b in disjoint_pairs(onto):
        for x in set(g.subjects(RDF.type, a)) & set(g.subjects(RDF.type, b)):
            problems.append(f"{short(x)} is both {short(a)} and {short(b)} (disjoint)")
    for x in g.subjects(RDF.type, OWL.Nothing):
        problems.append(f"{short(x)} is inferred to be owl:Nothing")
    for p in onto.subjects(RDF.type, OWL.IrreflexiveProperty):
        for s, o in g.subject_objects(p):
            if s == o:
                problems.append(f"{short(s)} {short(p)} itself (irreflexive)")
    for p in onto.subjects(RDF.type, OWL.FunctionalProperty):
        if (p, RDF.type, OWL.DatatypeProperty) in onto:
            vals = defaultdict(set)
            for s, o in g.subject_objects(p):
                vals[s].add(o)
            for s, vs in vals.items():
                if len(vs) > 1:
                    problems.append(f"{short(s)} has {len(vs)} values of functional {short(p)}")
    # OWL RL rules also report problems as rdfs:comment on owl:Nothing-like error nodes
    for s, o in g.subject_objects(RDFS.comment):
        if isinstance(o, Literal) and str(o).startswith("Error"):
            problems.append(str(o))
    return problems, inferred


# --------------------------------------------------------------------------- 4
def statistics(onto: Graph, data: Graph) -> str:
    g = onto + data
    rows = []
    q = """
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?class (COUNT(DISTINCT ?i) AS ?n) WHERE {
      ?i a ?c . ?c rdfs:subClassOf* ?class .
      FILTER (STRSTARTS(STR(?class), "%s"))
    } GROUP BY ?class ORDER BY DESC(?n)
    """ % AIT
    for r in g.query(q):
        rows.append((short(r["class"]), int(r["n"])))
    preds = defaultdict(int)
    for _, p, _ in data:
        preds[short(p)] += 1
    n_classes = len([c for c in onto.subjects(RDF.type, OWL.Class) if str(c).startswith(str(AIT))])
    n_op = len([c for c in onto.subjects(RDF.type, OWL.ObjectProperty) if str(c).startswith(str(AIT))])
    n_dp = len([c for c in onto.subjects(RDF.type, OWL.DatatypeProperty) if str(c).startswith(str(AIT))])
    used = {p for p in preds if p.startswith("ait:")}
    out = io.StringIO()
    out.write("| Metric | Value |\n|---|---:|\n")
    out.write(f"| Triples in the ontology | {len(onto)} |\n")
    out.write(f"| Triples in the knowledge graph (data) | {len(data)} |\n")
    out.write(f"| Classes defined (`ait:`) | {n_classes} |\n")
    out.write(f"| Object properties defined | {n_op} |\n")
    out.write(f"| Datatype properties defined | {n_dp} |\n")
    out.write(f"| `ait:` properties used in data | {len(used)} of {n_op + n_dp} |\n")
    out.write(f"| Distinct subjects in data | {len(set(data.subjects()))} |\n\n")
    out.write("| Class (incl. subclasses) | Instances |\n|---|---:|\n")
    for c, n in rows:
        out.write(f"| `{c}` | {n} |\n")
    unused = sorted({short(p) for p in list(onto.subjects(RDF.type, OWL.ObjectProperty)) +
                     list(onto.subjects(RDF.type, OWL.DatatypeProperty))
                     if str(p).startswith(str(AIT))} - used)
    if unused:
        out.write(f"\nProperties not asserted directly in the data: {', '.join('`'+u+'`' for u in unused)}.\n")
    return out.getvalue()


# --------------------------------------------------------------------------- 5
def md_escape(v: str) -> str:
    return v.replace("|", "\\|").replace("\n", " ")


def run_queries(g: Graph) -> dict[str, dict]:
    RESULTS.mkdir(exist_ok=True)
    out = {}
    for f in sorted(QUERIES.glob("*.rq")):
        text = f.read_text()
        res = g.query(text)
        key = f.stem.split("-")[0]
        if res.type == "CONSTRUCT":
            cg = Graph()
            for t in res:
                cg.add(t)
            cg.bind("schema", "https://schema.org/")
            cg.bind("aid", AID)
            ttl = cg.serialize(format="turtle")
            (RESULTS / f"{f.stem}.ttl").write_text(ttl)
            body = "\n".join(l for l in ttl.splitlines() if not l.startswith("@prefix")).strip()
            md = f"*{len(cg)} triples constructed:*\n\n```turtle\n{body}\n```\n"
            n = len(cg)
        else:
            vars_ = [str(v) for v in res.vars]
            rows = [[short(r[v]) for v in vars_] for r in res]
            with open(RESULTS / f"{f.stem}.csv", "w", newline="") as fh:
                w = csv.writer(fh)
                w.writerow(vars_)
                w.writerows(rows)
            md = "| " + " | ".join(vars_) + " |\n|" + "---|" * len(vars_) + "\n"
            for r in rows:
                md += "| " + " | ".join(md_escape(c) for c in r) + " |\n"
            md += f"\n*{len(rows)} rows.*\n"
            n = len(rows)
        (RESULTS / f"{f.stem}.md").write_text(md)
        # query text without the leading comment block
        q_lines = text.splitlines()
        comment = []
        while q_lines and q_lines[0].startswith("#"):
            comment.append(q_lines.pop(0).lstrip("# ").strip())
        common = ("PREFIX ait:", "PREFIX aid:", "PREFIX rdfs:", "PREFIX xsd:")
        q_lines = [l for l in q_lines if not l.startswith(common)]
        out[key] = {"file": f.name, "query": "\n".join(q_lines).strip(),
                    "title": " ".join(comment), "result": md, "rows": n}
        log(f"  {f.name}: {n} {'triples' if res.type == 'CONSTRUCT' else 'rows'}")
        if n == 0:
            errors.append(f"query {f.name} returned no results")
    return out


# --------------------------------------------------------------------------- 6
def shacl(onto: Graph, data: Graph, shapes: Graph, label: str):
    conforms, report_graph, report_text = validate(
        data, shacl_graph=shapes, ont_graph=onto, inference="none",
        advanced=True, allow_warnings=True)
    (RESULTS / f"shacl-{label}.txt").write_text(report_text)
    rows = []
    for r in report_graph.subjects(RDF.type, SH.ValidationResult):
        focus = report_graph.value(r, SH.focusNode)
        path = report_graph.value(r, SH.resultPath)
        msg = report_graph.value(r, SH.resultMessage)
        comp = report_graph.value(r, SH.sourceConstraintComponent)
        src = report_graph.value(r, SH.sourceShape)
        # find the node shape the result comes from
        node_shape = src
        if isinstance(src, BNode):
            node_shape = shapes.value(predicate=SH.property, object=src) or \
                         shapes.value(predicate=SH.sparql, object=src) or src
        rows.append((short(focus), short(node_shape).replace(
            "https://otavlna.github.io/4iz444-ai-tools-kg/shapes#", "aish:"),
            short(path) if path else "(SPARQL)",
            short(comp).replace("http://www.w3.org/ns/shacl#", "sh:"), str(msg).replace(str(AID), "aid:")))
    rows.sort()
    md = f"**Conforms:** `{str(conforms).lower()}` — {len(rows)} violation(s).\n\n"
    if rows:
        md += "| Focus node | Shape | Path | Constraint | Message |\n|---|---|---|---|---|\n"
        for r in rows:
            md += "| " + " | ".join(md_escape(c) for c in r) + " |\n"
    (RESULTS / f"shacl-{label}.md").write_text(md)
    log(f"  {label}: conforms={conforms}, {len(rows)} violations")
    return conforms, md


# --------------------------------------------------------------------------- 7
def label_of(g: Graph, t) -> str:
    return short(t).replace("ait:", "")


def diagram(onto: Graph) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    classes = sorted([c for c in onto.subjects(RDF.type, OWL.Class)
                      if isinstance(c, URIRef) and str(c).startswith(str(AIT))], key=str)
    attrs = defaultdict(list)
    edges = []

    def domains(p):
        d = onto.value(p, RDFS.domain)
        if isinstance(d, BNode):
            return list(Collection(onto, onto.value(d, OWL.unionOf)))
        return [d] if d is not None else []

    def chars(p):
        c = []
        for t, s in [(OWL.FunctionalProperty, "F"), (OWL.TransitiveProperty, "T"),
                     (OWL.SymmetricProperty, "S"), (OWL.IrreflexiveProperty, "I")]:
            if (p, RDF.type, t) in onto:
                c.append(s)
        return f" [{','.join(c)}]" if c else ""

    for p in sorted(onto.subjects(RDF.type, OWL.DatatypeProperty), key=str):
        if not str(p).startswith(str(AIT)):
            continue
        rng = short(onto.value(p, RDFS.range))
        for d in domains(p):
            attrs[d].append(f"{label_of(onto, p)} : {rng}{chars(p)}")
    inverse_skip = set()
    for p in sorted(onto.subjects(RDF.type, OWL.ObjectProperty), key=str):
        if not str(p).startswith(str(AIT)) or p in inverse_skip:
            continue
        inv = onto.value(p, OWL.inverseOf)
        name = label_of(onto, p) + chars(p)
        if inv is not None:
            inverse_skip.add(inv)
            name += f"\n(inverse: {label_of(onto, inv)})"
        for d in domains(p):
            edges.append((d, onto.value(p, RDFS.range), name))

    dot = ['digraph G {', '  rankdir=LR; splines=true; nodesep=0.5; ranksep=1.1;',
           '  graph [fontname="Helvetica", pad=0.3, bgcolor="white"];',
           '  node [shape=plain, fontname="Helvetica", fontsize=11];',
           '  edge [fontname="Helvetica", fontsize=9, color="#3b5b8c", fontcolor="#1f3a66"];']
    for c in classes:
        n = label_of(onto, c)
        rows = "".join(f'<TR><TD ALIGN="LEFT"><FONT POINT-SIZE="9">{a}</FONT></TD></TR>'
                       for a in attrs.get(c, []))
        color = "#fff4d6" if (c, RDFS.subClassOf, None) in onto and any(
            str(o).startswith(str(AIT)) for o in onto.objects(c, RDFS.subClassOf)) else "#e3ecfa"
        dot.append(f'  "{n}" [label=<<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="4" '
                   f'BGCOLOR="{color}"><TR><TD><B>{n}</B></TD></TR>{rows}</TABLE>>];')
    for d, r, name in edges:
        dot.append(f'  "{label_of(onto, d)}" -> "{label_of(onto, r)}" [label="{name}"];')
    for c in classes:
        for sup in onto.objects(c, RDFS.subClassOf):
            if str(sup).startswith(str(AIT)):
                dot.append(f'  "{label_of(onto, c)}" -> "{label_of(onto, sup)}" '
                           f'[arrowhead=empty, style=dashed, color="#888888", label="subClassOf", fontcolor="#666666"];')
    dot.append(f'  "LanguageModel" -> "ImageGenerationModel" [dir=both, arrowhead=none, arrowtail=none, '
               f'style=dotted, color="#b03030", label="disjointWith", fontcolor="#b03030", constraint=false];')
    dot.append("}")
    dot_path = FIGURES / "ontology.dot"
    dot_path.write_text("\n".join(dot))
    for fmt in ("svg", "png"):
        args = ["dot", f"-T{fmt}", str(dot_path), "-o", str(FIGURES / f"ontology.{fmt}")]
        if fmt == "png":
            args.insert(1, "-Gdpi=170")
        subprocess.run(args, check=True)
    log(f"  wrote {FIGURES.relative_to(ROOT)}/ontology.svg|png")


# --------------------------------------------------------------------------- 8
def assemble_report(queries: dict, stats: str, shacl_valid: str, shacl_invalid: str,
                    consistency: str) -> None:
    BUILD.mkdir(exist_ok=True)
    tpl = (ROOT / "report" / "report.md").read_text()

    def file_block(path: Path, lang: str) -> str:
        return f"```{lang}\n{path.read_text().strip()}\n```"

    def repl(m: re.Match) -> str:
        kind, arg = m.group(1), m.group(2)
        if kind == "QUERY":
            return f"```sparql\n{queries[arg]['query']}\n```"
        if kind == "RESULT":
            return queries[arg]["result"]
        if kind == "FILE":
            p = ROOT / arg
            return file_block(p, "turtle" if p.suffix == ".ttl" else "")
        if kind == "SHAPE":
            # extract one shape block from shapes.ttl by its local name
            text = SHAPES.read_text()
            mm = re.search(rf"^aish:{arg}\n.*?\.\n(?=\n|\Z)", text, re.S | re.M)
            return f"```turtle\n{mm.group(0).strip()}\n```"
        return m.group(0)

    out = re.sub(r"\{\{(QUERY|RESULT|FILE|SHAPE):([^}]+)\}\}", repl, tpl)
    out = (out.replace("{{STATS}}", stats)
              .replace("{{SHACL_VALID}}", shacl_valid)
              .replace("{{SHACL_INVALID}}", shacl_invalid)
              .replace("{{CONSISTENCY}}", consistency))
    left = re.findall(r"\{\{[^}]+\}\}", out)
    if left:
        errors.append(f"unresolved placeholders in report: {left}")
    (BUILD / "report.md").write_text(out)
    log("  wrote build/report.md")


def main() -> int:
    log("1. Parsing")
    onto, data, shapes, invalid = parse(ONTO), parse(DATA), parse(SHAPES), parse(INVALID)

    log("2. Documentation check")
    missing = check_documentation(onto)
    for m in missing:
        errors.append("documentation: " + m)
    log(f"  {'all classes and properties documented' if not missing else missing}")

    log("3. OWL 2 RL reasoning + consistency")
    problems, inferred = consistency_check(onto, data)
    for p in problems:
        errors.append("consistency: " + p)
    consistency = (f"OWL 2 RL closure (owlrl {owlrl.__version__}) over ontology + data inferred "
                   f"{inferred} additional triples; **{len(problems)} inconsistencies** found "
                   f"(disjoint-class membership, `owl:Nothing`, irreflexive and functional property violations).")
    log("  " + consistency)
    # sanity: the invalid data should also be checked but is expected to be inconsistent only via SHACL

    log("4. Statistics")
    stats = statistics(onto, data)

    log("5. SPARQL queries")
    g = Graph()
    g += onto
    g += data
    queries = run_queries(g)

    log("6. SHACL validation")
    ok, shacl_valid = shacl(onto, data, shapes, "valid")
    if not ok:
        errors.append("valid data does not conform to SHACL shapes")
    bad, shacl_invalid = shacl(onto, data + invalid, shapes, "invalid")
    if bad:
        errors.append("invalid data unexpectedly conforms")

    log("7. Diagram")
    diagram(onto)

    log("8. Report")
    assemble_report(queries, stats, shacl_valid, shacl_invalid, consistency)

    if errors:
        log("\nERRORS:")
        for e in errors:
            log("  - " + e)
        return 1
    log("\nBuild OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
