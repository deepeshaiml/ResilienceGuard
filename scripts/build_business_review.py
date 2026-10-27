#!/usr/bin/env python3
"""Create a ResilienceGuard business review from the retained Business Review PPTX."""

from __future__ import annotations

import argparse
from copy import deepcopy
from io import BytesIO
from pathlib import Path
import posixpath
import re
from zipfile import ZIP_DEFLATED, ZipFile
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REFERENCE = Path.home() / ".codex/plugins/cache/openai-curated-remote/openai-templates/0.1.1/skills/artifact-template-business-review/assets/reference.pptx"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    "--template",
    type=Path,
    default=DEFAULT_REFERENCE,
    metavar="PATH",
    help="path to the retained Business Review reference PPTX (default: local Codex template cache)",
)
REFERENCE = parser.parse_args().template.expanduser()
if not REFERENCE.is_file():
    raise SystemExit(
        f"Business Review template not found: {REFERENCE}\n"
        "Pass its location with --template /path/to/reference.pptx."
    )
OUTPUT = ROOT / "ResilienceGuard_Business_Review.pptx"

P = "http://schemas.openxmlformats.org/presentationml/2006/main"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
C = "http://schemas.openxmlformats.org/drawingml/2006/chart"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL = "http://schemas.openxmlformats.org/package/2006/relationships"
CT = "http://schemas.openxmlformats.org/package/2006/content-types"
S = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
XML = "http://www.w3.org/XML/1998/namespace"
NS = {"p": P, "a": A, "c": C, "r": R, "rel": REL, "ct": CT, "s": S}

for prefix, uri in (("p", P), ("a", A), ("c", C), ("r", R), ("s", S)):
    ET.register_namespace(prefix, uri)


def q(uri: str, local: str) -> str:
    return f"{{{uri}}}{local}"


def parse(raw: bytes) -> ET.Element:
    for _, (prefix, uri) in ET.iterparse(BytesIO(raw), events=("start-ns",)):
        ET.register_namespace(prefix or "", uri)
    return ET.fromstring(raw)


def xml_bytes(root: ET.Element) -> bytes:
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


with ZipFile(REFERENCE) as source:
    files = {name: source.read(name) for name in source.namelist()}


def shapes(slide_num: int) -> list[ET.Element]:
    root = parse(files[f"ppt/slides/slide{slide_num}.xml"])
    return root.findall(".//p:sp", NS)


def shape_name(shape: ET.Element) -> str:
    node = shape.find("./p:nvSpPr/p:cNvPr", NS)
    return node.get("name", "") if node is not None else ""


def shape_paragraphs(shape: ET.Element) -> list[ET.Element]:
    body = shape.find("./p:txBody", NS)
    return body.findall("./a:p", NS) if body is not None else []


def set_shape_text(shape: ET.Element, paragraphs: list[str]) -> None:
    body = shape.find("./p:txBody", NS)
    if body is None:
        raise ValueError(f"Shape has no text body: {shape_name(shape)}")
    existing = body.findall("./a:p", NS)
    if not existing:
        raise ValueError(f"Shape has no paragraph: {shape_name(shape)}")
    while len(existing) < len(paragraphs):
        clone = deepcopy(existing[-1])
        body.append(clone)
        existing.append(clone)
    for idx, paragraph in enumerate(existing):
        if idx >= len(paragraphs):
            body.remove(paragraph)
            continue
        text_nodes = paragraph.findall(".//a:t", NS)
        if not text_nodes:
            run = ET.Element(q(A, "r"))
            run_props = ET.SubElement(run, q(A, "rPr"), {"lang": "en-US"})
            text_node = ET.SubElement(run, q(A, "t"))
            text_node.text = paragraphs[idx]
            ppr = paragraph.find("./a:pPr", NS)
            paragraph.insert(list(paragraph).index(ppr) + 1 if ppr is not None else 0, run)
        else:
            text_nodes[0].text = paragraphs[idx]
            for extra in text_nodes[1:]:
                extra.text = ""


def set_named(slide_num: int, name: str, paragraphs: list[str], occurrence: int = 0) -> None:
    matches = [s for s in shapes(slide_num) if shape_name(s) == name]
    if occurrence >= len(matches):
        raise ValueError(f"Missing {name!r} occurrence {occurrence} on slide {slide_num}; found {len(matches)}")
    set_shape_text(matches[occurrence], paragraphs)


def set_named_starting(slide_num: int, name: str, starts: str, paragraphs: list[str]) -> None:
    matches = []
    for shape in shapes(slide_num):
        if shape_name(shape) != name:
            continue
        current = "".join(t.text or "" for t in shape.findall(".//a:t", NS))
        if current.startswith(starts):
            matches.append(shape)
    if not matches:
        raise ValueError(f"Missing {name!r} with text {starts!r} on slide {slide_num}")
    set_shape_text(matches[0], paragraphs)


def set_text_once(slide_num: int, old_text: str, replacement: str) -> None:
    found = []
    for shape in shapes(slide_num):
        current = "".join(t.text or "" for t in shape.findall(".//a:t", NS))
        if current == old_text:
            found.append(shape)
    if len(found) != 1:
        raise ValueError(f"Expected one match for {old_text!r} on slide {slide_num}; got {len(found)}")
    set_shape_text(found[0], [replacement])


def save_slide(slide_num: int) -> None:
    path = f"ppt/slides/slide{slide_num}.xml"
    root = parse(files[path])
    files[path] = xml_bytes(root)


def edit_slide(slide_num: int, edits: list[tuple[str, int, list[str]]]) -> None:
    path = f"ppt/slides/slide{slide_num}.xml"
    root = parse(files[path])
    all_shapes = root.findall(".//p:sp", NS)
    for name, occurrence, paragraphs in edits:
        matches = [s for s in all_shapes if shape_name(s) == name]
        if occurrence >= len(matches):
            raise ValueError(f"Missing {name!r} occurrence {occurrence} on slide {slide_num}; found {len(matches)}")
        set_shape_text(matches[occurrence], paragraphs)
    files[path] = xml_bytes(root)


def edit_slide_text(slide_num: int, replacements: list[tuple[str, list[str], int]]) -> None:
    """Replace by old concatenated text; occurrence counts exact-shape matches."""
    path = f"ppt/slides/slide{slide_num}.xml"
    root = parse(files[path])
    all_shapes = root.findall(".//p:sp", NS)
    for old, new_paragraphs, occurrence in replacements:
        matches = [s for s in all_shapes if "".join(t.text or "" for t in s.findall(".//a:t", NS)) == old]
        if occurrence >= len(matches):
            raise ValueError(f"Missing exact text {old!r} on slide {slide_num}; found {len(matches)}")
        set_shape_text(matches[occurrence], new_paragraphs)
    files[path] = xml_bytes(root)


def set_shape_text_from_cell(cell: ET.Element, value: str) -> None:
    paragraphs = cell.findall("./a:txBody/a:p", NS)
    if not paragraphs:
        raise ValueError("Table cell has no paragraph")
    nodes = paragraphs[0].findall(".//a:t", NS)
    if nodes:
        nodes[0].text = value
        for node in nodes[1:]:
            node.text = ""


# Cover and agenda.
edit_slide_text(1, [
    ("Enterprise Quarterly Business Review", ["ResilienceGuard Business Review"], 0),
    ("A structured review of Q1 2025 performance, strategic outcomes, and the operational plan for Q2. This deck covers our scorecard against targets, key initiatives delivered, value created, critical learnings, and the decisions needed to accelerate execution in the next quarter.", ["MVP readiness, synthetic evaluation, service-level findings, illustrative first-year economics, and decisions for a supervised pilot. This is a product-stage review, not a report of quarterly customer or revenue performance."], 0),
    ("Q3 2026", ["27 October 2026"], 0),
    ("Company or team name", ["ResilienceGuard · MVP 0.1.0"], 0),
])
edit_slide_text(2, [
    ("Meeting title with agenda slide", ["Business review agenda"], 0),
    ("Agenda", ["Agenda"], 0),
])
table_root = parse(files["ppt/slides/slide2.xml"])
agenda = table_root.find(".//a:tbl", NS)
agenda_rows = agenda.findall("./a:tr", NS)
agenda_items = [
    ("Executive verdict", "MVP review"),
    ("Scorecard and test results", "Evidence"),
    ("Service-level findings", "Scenario"),
    ("Commercial assumptions", "Planning"),
    ("Risks and gaps", "Controls"),
    ("Decisions and outlook", "Next steps"),
]
for row, (topic, owner) in zip(agenda_rows, agenda_items):
    cells = row.findall("./a:tc", NS)
    set_shape_text_from_cell(cells[1], topic)
    set_shape_text_from_cell(cells[2], owner)
files["ppt/slides/slide2.xml"] = xml_bytes(table_root)
# Executive summary.
edit_slide(3, [
    ("Google Shape;534;p58", 0, ["The local MVP is implemented: 10 backend tests passed, synthetic dependency checks matched expected labels, and three sample-file restore checks passed. No customer systems or production workloads were tested."]),
    ("Google Shape;534;p58", 1, ["MVP status"]),
    ("Google Shape;534;p58", 2, ["The 05:00 database copy matches its saved fingerprint but is one hour older than the two-hour data-loss target. The hospital app remains blocked because Directory Data Store has no backup record."]),
    ("Google Shape;534;p58", 3, ["The most important insight"]),
    ("Google Shape;534;p58", 4, ["Choose a pilot owner and three to five representative services. Confirm data owners, recovery targets, dependencies, and security requirements before setting pilot scope."]),
    ("Google Shape;534;p58", 5, ["Leadership decision needed"]),
    ("Google Shape;534;p58", 6, ["Ready for supervised evidence mapping and isolated file tests; not ready for production recovery or compliance claims."]),
    ("Rounded Rectangle 2", 0, ["MVP implemented"]),
    ("TextBox 13", 0, ["Bottom line"]),
])

# Scorecard.
edit_slide(4, [
    ("Google Shape;533;p58", 0, ["MVP scorecard: synthetic evaluation"]),
    ("Google Shape;534;p58", 0, ["Each fraction reports expected answers correctly classified. It does not estimate real-world recovery reliability."]),
    ("Google Shape;534;p58", 1, ["Measured results use known synthetic examples. Fixed reference time: 26 October 2026, 08:00 UTC."]),
    ("TextBox 13", 0, ["Backup rule checks"]),
    ("Content Placeholder 10", 0, ["Fingerprint 5/5 · backup age 5/5 · missing backup 4/4"]),
    ("TextBox 16", 0, ["Service blockers"]),
    ("Content Placeholder 10", 1, ["12/12 labels matched across 4 services and 3 disruptions"]),
    ("TextBox 18", 0, ["Sandbox file test"]),
    ("Content Placeholder 10", 2, ["3/3 sample checks passed; mean 0.581 ms per copy"]),
    ("TextBox 20", 0, ["Approval safety"]),
    ("Content Placeholder 10", 3, ["2/2 pending or scenario-untrusted restore attempts were blocked"]),
])

# Capabilities delivered.
edit_slide(5, [
    ("Google Shape;533;p58", 0, ["Delivered capabilities, measured at fixture scale"]),
    ("Google Shape;534;p58", 0, [
        "ResilienceGuard combines a synthetic service catalog, backup metadata, disruption scenarios, and a rule-based map of service requirements. It reports file presence, age, fingerprint match, location reachability, and restore result separately.",
        "A person can propose, approve or reject, and inspect a real copy of a registered sample in an isolated folder. The system records the result and exports an evidence report; the original sample stays read-only.",
    ]),
    ("Google Shape;534;p58", 1, ["No production connector, malware scan, or live database restore is included."]),
    ("TextBox 27", 0, ["Backup evidence"]),
    ("Content Placeholder 10", 0, ["File found · age vs target · fingerprint · location status"]),
    ("TextBox 5", 0, ["Dependencies and scenarios"]),
    ("Content Placeholder 10", 1, ["Three disruptions recalculate available copies and service blockers"]),
    ("TextBox 8", 0, ["Human-gated test"]),
    ("Content Placeholder 10", 2, ["Only an approved, registered synthetic file reaches the test folder"]),
])

# Service-level segment results.
edit_slide(6, [
    ("Title 3", 0, ["Service results under primary-site loss"]),
    ("Content Placeholder 9", 1, ["Clinical database", "The 05:00 West copy matches its fingerprint but is 3 hours old against a 2-hour data-loss target. It may be tested with the gap visible."]),
    ("Content Placeholder 9", 0, ["Identity and directory", "Identity depends on Directory Store. No directory backup record exists, so identity remains blocked."]),
    ("Content Placeholder 10", 0, ["Hospital application", "The app needs the database and identity. It remains blocked through identity until the missing directory prerequisite is addressed."]),
    ("Google Shape;534;p58", 0, [
        "The physical-disaster scenario removes the primary site and East backup location; the West location and recovery network remain reachable.",
        "The 07:00 database sample was deliberately altered and fails its fingerprint check. Malware status is unknown because no scanner ran.",
    ]),
    ("Google Shape;534;p58", 1, ["The physical-disaster case uses synthetic data; no hospital or customer records are present."]),
])

# Proven results and remaining gaps.
edit_slide(7, [
    ("Google Shape;533;p58", 0, ["Current readiness: what is proven and what remains open"]),
    ("Google Shape;534;p58", 0, [
        "Delivered: synthetic service and backup inventory, fixed-seed scenario assessment, and rule-based dependency blockers.",
        "Tested: 10 backend tests passed; expected labels matched; three isolated sample-file copies passed fingerprint and JSON checks.",
        "Workflow: a proposal stays pending until a person approves it. Test results and audit events are recorded.",
    ]),
    ("Google Shape;534;p58", 1, [
        "Not tested: customer integrations, PostgreSQL or application startup, malware scanning, or actual service recovery time.",
        "Governance gap: no authenticated roles, multi-person approval, or immutable external audit. Do not use this MVP to change production.",
        "AI status: fallback action IDs matched the rule-only baseline. Local model inference and generative accuracy were not measured.",
    ]),
    ("Google Shape;534;p58", 2, ["MVP evidence, limitations, and proposed next steps."]),
])

# Product thesis and evidence table.
edit_slide(8, [
    ("Google Shape;533;p58", 0, ["A correct file check does not prove the hospital service can return"]),
    ("Google Shape;534;p58", 0, ["At 08:00, the 05:00 database copy is one hour outside its data-loss target, and the missing Directory Store backup blocks identity. ResilienceGuard makes both limits visible; it has not restored the application."]),
])
slide9 = parse(files["ppt/slides/slide9.xml"])
slide9_shapes = slide9.findall(".//p:sp", NS)
for name, occurrence, text in [
    ("Google Shape;533;p58", 0, ["Illustrative first-year economics (USD; assumptions only)"]),
    ("Google Shape;534;p58", 1, [
        "Per customer: $78k revenue; $18k direct cost.",
    ]),
    ("Google Shape;534;p58", 0, ["Gross profit = revenue − cost. Net subtracts fixed overhead. All figures are assumptions."]),
]:
    matches = [s for s in slide9_shapes if shape_name(s) == name]
    set_shape_text(matches[occurrence], text)
table = slide9.find(".//a:tbl", NS)
rows = table.findall("./a:tr", NS)
row_heights = [int(row.get("h", "0")) for row in rows]
total_height = sum(row_heights)
scenario_rows = [
    ["Customers", "Revenue", "Direct costs", "Gross profit"],
    ["1", "$78,000", "$18,000", "$60,000"],
    ["5", "$390,000", "$90,000", "$300,000"],
    ["10", "$780,000", "$180,000", "$600,000"],
    ["25", "$1,950,000", "$450,000", "$1,500,000"],
]
keep_rows = rows[:5]
for index, (row, values) in enumerate(zip(keep_rows, scenario_rows)):
    cells = row.findall("./a:tc", NS)
    for cell, value in zip(cells, values):
        set_shape_text_from_cell(cell, value)
    row.set("h", str(total_height // 5 + (total_height % 5 if index == 4 else 0)))
for row in rows[5:]:
    table.remove(row)
files["ppt/slides/slide9.xml"] = xml_bytes(slide9)

# First-year revenue and direct-cost chart plus explanatory cards.
edit_slide(10, [
    ("Google Shape;533;p58", 0, ["First-year revenue and direct costs by customer count"]),
    ("TextBox 12", 0, ["Revenue per customer"]),
    ("Content Placeholder 10", 0, ["$78k: implementation, annual license, and support"]),
    ("TextBox 14", 0, ["Direct cost assumption"]),
    ("Content Placeholder 10", 1, ["$18k per customer for delivery and support"]),
    ("TextBox 17", 0, ["Recurring revenue mix"]),
    ("Content Placeholder 10", 2, ["$48k license + $12k support; implementation is one-time"]),
])

# Gross profit versus overhead, with net results at 10 and 25 customers.
edit_slide(11, [
    ("Google Shape;533;p58", 0, ["Gross profit versus assumed fixed overhead"]),
    ("Content Placeholder 9", 0, ["$80k"]),
    ("Content Placeholder 15", 0, ["Illustrative net result at 10 customers, before tax"]),
    ("Content Placeholder 9", 1, ["$750k"]),
    ("Content Placeholder 15", 1, ["Illustrative net result at 25 customers, before tax"]),
    ("Content Placeholder 2", 0, ["The model assumes fixed overhead of $260k / $360k / $520k / $750k at 1 / 5 / 10 / 25 customers. Net result is gross profit minus overhead; tax, financing, churn, and acquisition costs are excluded."]),
])

# Proposed pilot path: dates remain uncommitted.
edit_slide(12, [
    ("Title 10", 0, ["Proposed pilot path; dates to be agreed"]),
    ("Content Placeholder 15", 0, ["Scope the pilot", "Choose three to five services; confirm owners, data-loss and recovery-time targets, and dependencies."]),
    ("Text Placeholder 16", 0, ["Run a joint exercise", "Review primary-site loss, ransomware, and a combined power/network disruption."]),
    ("Content Placeholder 17", 0, ["Test and review evidence", "Approve a synthetic isolated copy; record its result, observed duration, and known gaps."]),
    ("Content Placeholder 15", 1, ["TBD"]),
    ("Content Placeholder 15", 2, ["TBD"]),
    ("Content Placeholder 15", 3, ["TBD"]),
])

# Proposed strategic priorities, without implying committed delivery dates.
edit_slide(13, [
    ("Google Shape;533;p58", 0, ["Proposed priorities: sequence only; timing not committed"]),
    ("Google Shape;969;p80", 0, ["Buyer and operator interviews"]),
    ("Google Shape;966;p80", 0, ["Map service owners, targets, and dependencies"]),
    ("Google Shape;963;p80", 0, ["Add authenticated roles and independent approval"]),
    ("Google Shape;955;p80", 0, ["Build vendor-neutral backup adapters"]),
    ("Google Shape;960;p80", 0, ["Malware scan + app/database health checks"]),
    ("Google Shape;957;p80", 0, ["Run a supervised pilot and measure customer value"]),
])
slide13 = parse(files["ppt/slides/slide13.xml"])
timeline = slide13.find(".//a:tbl", NS)
for cell, value in zip(timeline.findall("./a:tr/a:tc", NS), ["Discovery", "Pilot", "Controls", "Integrations", "Validation"]):
    set_shape_text_from_cell(cell, value)
files["ppt/slides/slide13.xml"] = xml_bytes(slide13)

# Closing decisions.
edit_slide(14, [
    ("Title 3", 0, ["Decisions to move toward a pilot"]),
    ("Subtitle 4", 0, ["Name a pilot owner", "Agree on service scope and evidence", "Confirm success measures and security gates"]),
])


def replace_chart_cache(chart_path: str, title_text: str, series: list[tuple[str, list[float]]]) -> None:
    root = parse(files[chart_path])
    chart_title = root.find("./c:chart/c:title", NS)
    if chart_title is None:
        raise ValueError(f"Chart title missing in {chart_path}")
    tx = chart_title.find("./c:tx", NS)
    if tx is None:
        tx = ET.Element(q(C, "tx"))
        chart_title.insert(0, tx)
    for child in list(tx):
        tx.remove(child)
    rich = ET.SubElement(tx, q(C, "rich"))
    ET.SubElement(rich, q(A, "bodyPr"))
    ET.SubElement(rich, q(A, "lstStyle"))
    paragraph = ET.SubElement(rich, q(A, "p"))
    ppr = ET.SubElement(paragraph, q(A, "pPr"))
    default = ET.SubElement(ppr, q(A, "defRPr"), {"lang": "en-US", "sz": "1200"})
    solid = ET.SubElement(default, q(A, "solidFill"))
    ET.SubElement(solid, q(A, "schemeClr"), {"val": "tx1"})
    run = ET.SubElement(paragraph, q(A, "r"))
    ET.SubElement(run, q(A, "rPr"), {"lang": "en-US", "sz": "1200"})
    ET.SubElement(run, q(A, "t")).text = title_text
    ET.SubElement(paragraph, q(A, "endParaRPr"), {"lang": "en-US"})

    categories = ["1", "5", "10", "25"]
    series_nodes = root.findall(".//c:ser", NS)
    for ser, (name, values) in zip(series_nodes, series):
        name_pt = ser.find("./c:tx/c:strRef/c:strCache/c:pt/c:v", NS)
        if name_pt is not None:
            name_pt.text = name
        cat_cache = ser.find("./c:cat/c:strRef/c:strCache", NS)
        if cat_cache is not None:
            count = cat_cache.find("./c:ptCount", NS)
            if count is not None:
                count.set("val", str(len(categories)))
            for point, value in zip(cat_cache.findall("./c:pt", NS), categories):
                val = point.find("./c:v", NS)
                if val is not None:
                    val.text = value
        num_cache = ser.find("./c:val/c:numRef/c:numCache", NS)
        if num_cache is not None:
            fmt = num_cache.find("./c:formatCode", NS)
            if fmt is not None:
                fmt.text = "0"
            count = num_cache.find("./c:ptCount", NS)
            if count is not None:
                count.set("val", str(len(values)))
            points = num_cache.findall("./c:pt", NS)
            for point, value in zip(points, values):
                val = point.find("./c:v", NS)
                if val is not None:
                    val.text = str(value)
    files[chart_path] = xml_bytes(root)


def update_embedded_workbook(chart_path: str, series: list[tuple[str, list[float]]]) -> None:
    rel_path = f"ppt/charts/_rels/{Path(chart_path).name}.rels"
    rels = parse(files[rel_path])
    workbook_rel = next(r for r in rels if r.get("Type", "").endswith("/package"))
    embedded_path = posixpath.normpath(posixpath.join("ppt/charts", workbook_rel.get("Target")))
    with ZipFile(BytesIO(files[embedded_path])) as workbook_zip:
        wb = {n: workbook_zip.read(n) for n in workbook_zip.namelist()}
    shared = parse(wb["xl/sharedStrings.xml"])
    strings = shared.findall("./s:si", NS)
    labels = [series[0][0], series[1][0], "", "1", "5", "10", "25", " "]
    for item, value in zip(strings, labels):
        text_node = item.find("./s:t", NS)
        if text_node is None:
            text_node = ET.SubElement(item, q(S, "t"))
        text_node.text = value
    shared.set("uniqueCount", str(len(strings)))
    wb["xl/sharedStrings.xml"] = xml_bytes(shared)

    sheet = parse(wb["xl/worksheets/sheet1.xml"])
    dim = sheet.find("./s:dimension", NS)
    if dim is not None:
        dim.set("ref", "A1:C5")
    for row in sheet.findall("./s:sheetData/s:row", NS):
        row.set("spans", "1:3")
        for cell in list(row.findall("./s:c", NS)):
            if cell.get("r", "").startswith("D"):
                row.remove(cell)
    for column, idx in (("B1", 0), ("C1", 1)):
        cell = sheet.find(f".//s:c[@r='{column}']", NS)
        if cell is not None:
            cell.set("t", "s")
            cell.find("./s:v", NS).text = str(idx)
    for rnum, label_idx in enumerate((3, 4, 5, 6), start=2):
        cell = sheet.find(f".//s:c[@r='A{rnum}']", NS)
        cell.set("t", "s")
        cell.find("./s:v", NS).text = str(label_idx)
        for column, values in (("B", series[0][1]), ("C", series[1][1])):
            target = sheet.find(f".//s:c[@r='{column}{rnum}']", NS)
            target.find("./s:v", NS).text = str(values[rnum - 2])
    wb["xl/worksheets/sheet1.xml"] = xml_bytes(sheet)

    table = parse(wb["xl/tables/table1.xml"])
    table.set("ref", "A1:C5")
    auto_filter = table.find("./s:autoFilter", NS)
    if auto_filter is not None:
        auto_filter.set("ref", "A1:C5")
    table_columns = table.find("./s:tableColumns", NS)
    if table_columns is not None:
        columns = table_columns.findall("./s:tableColumn", NS)
        for col in columns[3:]:
            table_columns.remove(col)
        table_columns.set("count", "3")
        names = ["Customer count", series[0][0], series[1][0]]
        for col, name in zip(table_columns.findall("./s:tableColumn", NS), names):
            col.set("name", name)
    wb["xl/tables/table1.xml"] = xml_bytes(table)

    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as workbook_zip:
        for name, data in wb.items():
            workbook_zip.writestr(name, data)
    files[embedded_path] = output.getvalue()


revenue_cost = [("Revenue ($000s)", [78, 390, 780, 1950]), ("Direct costs ($000s)", [18, 90, 180, 450])]
profit_overhead = [("Gross profit ($000s)", [60, 300, 600, 1500]), ("Fixed overhead ($000s)", [260, 360, 520, 750])]
replace_chart_cache("ppt/charts/chart1.xml", "Revenue and direct costs · USD thousands", revenue_cost)
replace_chart_cache("ppt/charts/chart2.xml", "Gross profit and fixed overhead · USD thousands", profit_overhead)
update_embedded_workbook("ppt/charts/chart1.xml", revenue_cost)
update_embedded_workbook("ppt/charts/chart2.xml", profit_overhead)


notes = {
    1: "This is a product-stage business review, not a report of a completed sales quarter. The MVP runs against invented hospital-style data. Its measured results cover rule checks and a few local sample-file copies only. Revenue and cost figures later in the deck are illustrative planning assumptions, not market-verified prices or actual customers.",
    2: "We will review the MVP verdict, the synthetic scorecard, service-level findings, the illustrative economics, risks, and the proposed pilot decisions. No customer or production data is used in this review.",
    3: "The local MVP is implemented and its backend suite passed 10 of 10 tests. The synthetic checks matched expected labels. Three actual file-copy runs passed the sample file fingerprint and JSON structure checks. The most important limitation is that a database file check does not restore the hospital application. Ask leadership to name a pilot owner and identify a small set of services for a future supervised assessment; no pilot or customer commitment exists yet.",
    4: "Each fraction is correct classifications divided by the fixed synthetic examples checked. For example, 5/5 means all five known file cases matched their expected fingerprint label. The dependency matrix checked four services across three scenarios. The 0.581 millisecond average measures file copy, fingerprint comparison, and simple JSON validation; it is not application recovery time or a service-level objective result. These numbers do not estimate real-world reliability.",
    5: "The MVP imports synthetic service and backup information, checks age and file fingerprints, applies three disruption scenarios, follows service requirements, and records a human decision. The test writes a registered synthetic file to a separate local folder and reports what happened. It does not scan for malware, connect to backup vendors, restore a PostgreSQL database, or modify production.",
    6: "At the fixed 08:00 demo time, the 05:00 West database file matches its saved fingerprint but is three hours old. The configured data-loss target is two hours, so the candidate is one hour outside target. It can be tested with that gap clearly displayed. The 07:00 file was deliberately altered and does not match. Directory Store has no backup record; that blocks identity and consequently the hospital app. Malware status stays unknown because no scanner ran.",
    7: "The current evidence proves the synthetic rules and file-level workflow run as expected. It does not establish actual recovery for any hospital or utility. Production deployment would require identity and role controls, independent approvals, immutable audit protection, vendor integrations, and workload-specific restore validation. The optional local language model was not run; its accuracy is unmeasured. The deterministic fallback matched the rule-only action IDs.",
    8: "This is the central business insight: backup file quality is only one part of recovery readiness. A file may match the saved fingerprint but be older than the data-loss target, and a separate missing directory copy can block identity. The current service assessment surfaces both issues; it does not claim that the hospital application has been restored.",
    9: "The table uses four customer-count scenarios from the business case. First-year revenue assumes an 18-thousand-dollar implementation fee, a 48-thousand-dollar annual license, and 12-thousand-dollar annual support per customer. Direct costs are assumed at 18-thousand dollars per customer. Gross profit is revenue less direct costs. None of these prices or delivery costs is market-verified, and the table is not a forecast.",
    10: "The chart compares assumed first-year revenue and direct delivery cost at one, five, ten, and twenty-five customers. The horizontal groups are customer counts; values are thousands of US dollars. Revenue includes implementation, license, and support. Direct cost is the planning assumption per customer multiplied by customer count. The cards separate recurring fees from one-time implementation work.",
    11: "This chart compares gross profit with assumed fixed business overhead. Under the current assumptions, net result is negative 200-thousand dollars at one customer, negative 60-thousand at five, positive 80-thousand at ten, and positive 750-thousand at twenty-five. The large cards highlight the last two scenarios. These are illustrative, pre-tax calculations and exclude customer acquisition costs, churn, financing, and taxes; they should not be presented as a forecast.",
    12: "This is a proposed pilot sequence, not a scheduled commitment. First agree on service owners, targets, and dependencies. Then review the three synthetic disruption cases with operators. Finally, obtain explicit approval for an isolated synthetic file test and review its evidence. Dates remain to be agreed with a pilot organization.",
    13: "This is a planning view of recommended follow-up work, not a funded or dated delivery plan. Priorities come from known MVP gaps: buyer and operator interviews, service mapping, independent approvals and audit hardening, backup-source adapters, malware scanning and isolated application/database checks, and pilot measurement. The bar positions suggest sequence only; timing and effort require scoping.",
    14: "Close by asking for three decisions: identify an accountable pilot owner, agree which services and evidence to include, and set measurable success criteria with the required security gates. A pilot would validate the problem and implementation effort; it would not establish guaranteed risk reduction or production readiness.",
}


def notes_body_shape(root: ET.Element) -> ET.Element:
    for shape in root.findall(".//p:sp", NS):
        ph = shape.find("./p:nvSpPr/p:nvPr/p:ph", NS)
        if ph is not None and ph.get("type") == "body":
            return shape
    raise ValueError("Speaker-notes body placeholder not found")


def set_note_body(shape: ET.Element, text: str) -> None:
    txbody = shape.find("./p:txBody", NS)
    paragraph = txbody.find("./a:p", NS)
    for child in list(paragraph):
        if child.tag != q(A, "pPr"):
            paragraph.remove(child)
    run = ET.Element(q(A, "r"))
    ET.SubElement(run, q(A, "rPr"), {"lang": "en-US", "dirty": "0"})
    text_node = ET.SubElement(run, q(A, "t"))
    text_node.set(q(XML, "space"), "preserve")
    text_node.text = text
    ppr = paragraph.find("./a:pPr", NS)
    paragraph.insert(list(paragraph).index(ppr) + 1 if ppr is not None else 0, run)
    ET.SubElement(paragraph, q(A, "endParaRPr"), {"lang": "en-US"})


slide_to_note = {}
for slide_num in range(1, 15):
    relpath = f"ppt/slides/_rels/slide{slide_num}.xml.rels"
    relroot = parse(files[relpath]) if relpath in files else None
    note_rel = None if relroot is None else next((x for x in relroot if x.get("Type", "").endswith("/notesSlide")), None)
    if note_rel is not None:
        slide_to_note[slide_num] = posixpath.normpath(posixpath.join("ppt/slides", note_rel.get("Target")))

if 12 not in slide_to_note:
    # The retained reference omitted notes for slide 12; add a notes slide by cloning its notes layout.
    note_path = "ppt/notesSlides/notesSlide14.xml"
    note_relpath = "ppt/notesSlides/_rels/notesSlide14.xml.rels"
    template_notes = parse(files["ppt/notesSlides/notesSlide13.xml"])
    files[note_path] = xml_bytes(template_notes)
    rels = parse(files["ppt/notesSlides/_rels/notesSlide13.xml.rels"])
    for rel in rels:
        if rel.get("Type", "").endswith("/slide"):
            rel.set("Target", "../slides/slide12.xml")
    files[note_relpath] = xml_bytes(rels)
    slide_rels_path = "ppt/slides/_rels/slide12.xml.rels"
    slide_rels = parse(files[slide_rels_path])
    used_ids = {item.get("Id") for item in slide_rels}
    rid = "rIdNotes"
    while rid in used_ids:
        rid += "1"
    relation = ET.SubElement(slide_rels, q(REL, "Relationship"), {
        "Id": rid,
        "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesSlide",
        "Target": "../notesSlides/notesSlide14.xml",
    })
    files[slide_rels_path] = xml_bytes(slide_rels)
    types = parse(files["[Content_Types].xml"])
    ET.SubElement(types, q(CT, "Override"), {
        "PartName": "/ppt/notesSlides/notesSlide14.xml",
        "ContentType": "application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml",
    })
    files["[Content_Types].xml"] = xml_bytes(types)
    slide_to_note[12] = note_path

for slide_num, note_text in notes.items():
    note_path = slide_to_note[slide_num]
    root = parse(files[note_path])
    set_note_body(notes_body_shape(root), note_text)
    files[note_path] = xml_bytes(root)

with ZipFile(OUTPUT, "w", ZIP_DEFLATED) as target:
    for name, data in files.items():
        target.writestr(name, data)

print(f"Created {OUTPUT} from retained Business Review template ({len(slide_to_note)} slides with speaker notes).")
