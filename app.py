
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from html import escape
import json

from tool import prepare_evidence
from model import analyze_opportunity

app = FastAPI(title="OpportunityShield")

PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>OpportunityShield</title>
<style>
* { box-sizing: border-box; }
body {
    margin: 0;
    font-family: Arial, sans-serif;
    background: #f1f5f9;
    color: #172033;
}
header {
    background: #102a56;
    color: white;
    text-align: center;
    padding: 30px 16px;
}
header h1 { margin: 0 0 10px; font-size: 32px; }
header p { margin: 7px 0; color: #dbeafe; }
main { max-width: 900px; margin: 25px auto; padding: 0 16px; }
.card {
    background: white;
    border-radius: 14px;
    padding: 24px;
    margin-bottom: 20px;
    box-shadow: 0 4px 16px #0f172a0c;
}
label { display: block; margin-top: 17px; font-weight: bold; }
input, textarea, select {
    width: 100%;
    padding: 12px;
    margin-top: 7px;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    font: inherit;
    background: white;
}
textarea { min-height: 140px; resize: vertical; }
button {
    width: 100%;
    border: 0;
    border-radius: 8px;
    padding: 14px;
    margin-top: 22px;
    background: #2563eb;
    color: white;
    font-size: 16px;
    font-weight: bold;
    cursor: pointer;
}
button:hover { background: #1d4ed8; }
.muted { color: #64748b; font-size: 13px; line-height: 1.6; }
.hidden { display: none; }
.risk { border-left: 8px solid #64748b; }
.high { background: #fef2f2; border-color: #dc2626; }
.medium { background: #fefce8; border-color: #ca8a04; }
.low { background: #f0fdf4; border-color: #16a34a; }
.unknown { background: #f8fafc; border-color: #64748b; }
.risk-title { font-size: 25px; font-weight: bold; margin: 10px 0; }
.high .risk-title { color: #b91c1c; }
.medium .risk-title { color: #a16207; }
.low .risk-title { color: #15803d; }
.unknown .risk-title { color: #475569; }
.score { font-size: 30px; font-weight: bold; }
.error {
    color: #991b1b;
    background: #fef2f2;
    border: 1px solid #fecaca;
}
.result { white-space: pre-wrap; overflow-wrap: anywhere; line-height: 1.6; }
.finding {
    border: 1px solid #e2e8f0;
    border-radius: 9px;
    padding: 14px;
    margin-top: 12px;
}
.tag {
    display: inline-block;
    padding: 5px 9px;
    border-radius: 20px;
    background: #e2e8f0;
    font-size: 12px;
    font-weight: bold;
}
footer { text-align: center; color: #64748b; padding: 20px; font-size: 13px; }
@media(max-width:600px) {
    .card { padding: 17px; }
    header h1 { font-size: 27px; }
}
</style>
</head>
<body>
<header>
<h1>🛡️ OpportunityShield</h1>
<p>Check internship and job offers for warning signs.</p>
<p>Powered by your local Ollama model — no API key.</p>
</header>

<main>
<section class="card">
<h2>🔍 Analyze an opportunity</h2>

<form method="post" action="/analyze">
<label for="mode">Analysis mode</label>
<select name="mode" id="mode" onchange="toggleSecond()">
<option value="single" {{single_selected}}>Check one internship message</option>
<option value="compare" {{compare_selected}}>Compare two documents</option>
</select>

<label for="title">First document name</label>
<input id="title" name="title" value="{{title}}" placeholder="Internship Offer Email">

<label for="document">First internship message</label>
<textarea id="document" name="document" required placeholder="Paste the internship email here...">{{document}}</textarea>

<div id="second">
<label for="title2">Second document name</label>
<input id="title2" name="title2" value="{{title2}}" placeholder="Official Internship Posting">

<label for="document2">Second document text</label>
<textarea id="document2" name="document2" placeholder="Paste the second document here...">{{document2}}</textarea>
</div>

<label for="domain">Official company website domain (optional)</label>
<input id="domain" name="domain" value="{{domain}}" placeholder="company.com">

<label for="email">Recruiter email (optional)</label>
<input id="email" name="email" type="email" value="{{email}}" placeholder="recruiter@company.com">

<button type="submit">Analyze Opportunity</button>
</form>

<p class="muted">
Never share passwords, OTPs, UPI PINs, or banking security codes.
A low score does not prove that an offer is genuine.
</p>
</section>

{{result}}

<footer>OpportunityShield · FastAPI + Ollama · Runs locally</footer>
</main>

<script>
function toggleSecond() {
    const compare = document.getElementById("mode").value === "compare";
    document.getElementById("second").classList.toggle("hidden", !compare);
    document.getElementById("document2").required = compare;
}
toggleSecond();
</script>
</body>
</html>
"""


def render_page(result="", mode="single", title="", document="",
                title2="", document2="", domain="", email=""):
    values = {
        "{{single_selected}}": "selected" if mode == "single" else "",
        "{{compare_selected}}": "selected" if mode == "compare" else "",
        "{{title}}": escape(title),
        "{{document}}": escape(document),
        "{{title2}}": escape(title2),
        "{{document2}}": escape(document2),
        "{{domain}}": escape(domain),
        "{{email}}": escape(email),
        "{{result}}": result,
    }

    page = PAGE
    for key, value in values.items():
        page = page.replace(key, value)
    return page


def risk_class_for(score):
    if score >= 60:
        return "high", "🔴 High risk"
    if score >= 25:
        return "medium", "🟡 Medium risk"
    if score > 0:
        return "low", "🟢 Low detected risk"
    return "unknown", "⚪ Insufficient warning evidence"


def format_report(report, score):
    css_class, label = risk_class_for(score)

    parts = [
        '<section class="card risk ' + css_class + '">',
        '<h2>📋 Risk assessment</h2>',
        '<div class="risk-title">' + escape(label) + '</div>',
        '<div class="score">' + str(score) + '/100</div>',
        '<p>' + escape(str(report.get("summary", "Analysis completed."))) + '</p>',
        '<p class="muted">This is a preliminary warning indicator, '
        'not proof that an offer is genuine or fraudulent.</p>',
        '</section>'
    ]

    findings = report.get("findings", [])
    if isinstance(findings, list) and findings:
        parts.append('<section class="card"><h2>🚩 Findings</h2>')

        for item in findings:
            if not isinstance(item, dict):
                continue

            severity = str(item.get("severity", "Information"))
            parts.append(
                '<div class="finding"><span class="tag">' +
                escape(severity) + '</span>'
            )
            parts.append(
                '<h3>' +
                escape(str(item.get("category", "Finding"))) +
                '</h3>'
            )
            parts.append(
                '<p>' + escape(str(item.get("details", ""))) + '</p>'
            )

            if item.get("evidence"):
                parts.append(
                    '<p><b>Evidence:</b> ' +
                    escape(str(item["evidence"])) + '</p>'
                )

            if item.get("recommendation"):
                parts.append(
                    '<p><b>Suggested action:</b> ' +
                    escape(str(item["recommendation"])) + '</p>'
                )

            parts.append('</div>')

        parts.append('</section>')

    sections = [
        ("matching_details", "🔎 Matching details"),
        ("questions_to_ask", "❓ Questions to ask"),
        ("next_steps", "✅ Recommended next steps"),
        ("limitations", "ℹ️ Limitations"),
    ]

    for key, heading in sections:
        items = report.get(key, [])

        if isinstance(items, list) and items:
            parts.append(
                '<section class="card"><h2>' +
                heading + '</h2><ul>'
            )

            for item in items:
                if isinstance(item, dict):
                    item = json.dumps(item, ensure_ascii=False)
                parts.append('<li>' + escape(str(item)) + '</li>')

            parts.append('</ul></section>')

    parts.append(
        '<details class="card"><summary>View complete report</summary>'
        '<pre class="result">' +
        escape(json.dumps(report, indent=2, ensure_ascii=False)) +
        '</pre></details>'
    )

    return "".join(parts)


@app.get("/", response_class=HTMLResponse)
def home():
    return render_page()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze", response_class=HTMLResponse)
def analyze(
    mode: str = Form("single"),
    title: str = Form(""),
    document: str = Form(""),
    title2: str = Form(""),
    document2: str = Form(""),
    domain: str = Form(""),
    email: str = Form(""),
):
    mode = mode if mode in ("single", "compare") else "single"

    common = {
        "mode": mode,
        "title": title,
        "document": document,
        "title2": title2,
        "document2": document2,
        "domain": domain,
        "email": email,
    }

    if not document.strip():
        return render_page(
            '<section class="card error"><h2>Missing document</h2>'
            '<p>Please paste the first internship message.</p></section>',
            **common
        )

    if mode == "compare" and not document2.strip():
        return render_page(
            '<section class="card error"><h2>Missing second document</h2>'
            '<p>Please paste the second document for comparison.</p></section>',
            **common
        )

    documents = [{
        "id": "D1",
        "title": title.strip() or "Internship Message",
        "content": document.strip(),
    }]

    if mode == "compare":
        documents.append({
            "id": "D2",
            "title": title2.strip() or "Second Document",
            "content": document2.strip(),
        })

    try:
        evidence = prepare_evidence(
            documents,
            official_domain=domain.strip(),
            recruiter_email=email.strip(),
        )

        report = analyze_opportunity(evidence)

        if not isinstance(report, dict):
            raise ValueError("The AI returned an unexpected report format.")

        score = report.get("risk_score")

        if score is None and isinstance(evidence, dict):
            score = evidence.get("risk_score", 0)

        try:
            score = max(0, min(100, int(score or 0)))
        except (TypeError, ValueError):
            score = 0

        return render_page(format_report(report, score), **common)

    except Exception as exc:
        message = (
            f"{type(exc).__name__}: {exc}\n\n"
            "Check that Ollama is running and gemma3:1b is installed. "
            "If the error mentions document fields, check tool.py."
        )

        return render_page(
            '<section class="card error"><h2>Analysis failed</h2>'
            '<pre class="result">' + escape(message) +
            '</pre></section>',
            **common
        )
