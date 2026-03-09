from flask import Flask, render_template, request, jsonify, redirect, url_for
import json, os, urllib.request, urllib.error
from collections import defaultdict

app = Flask(__name__)

# ── In-memory store (replace with SQLite/Postgres for production) ──────────
entries = [
    {"id": 1, "segment_id": "FGD1_023", "snippet": "Delayed payments from government procurement have made it difficult for publishers to sustain operations.", "domain": "Governance", "indicator_code": "G2", "indicator_name": "Payment Delay Risk", "severity": 5, "stakeholder": "Publisher", "region": "NCR", "session": "FGD1"},
    {"id": 2, "segment_id": "FGD2_041", "snippet": "Distribution to remote provinces is expensive and often delayed due to transport limitations.", "domain": "Distribution", "indicator_code": "D1", "indicator_name": "Logistics Cost Burden", "severity": 4, "stakeholder": "Publisher", "region": "Visayas", "session": "FGD2"},
    {"id": 3, "segment_id": "FGD1_044", "snippet": "Printing costs have increased significantly due to dependence on imported paper and ink.", "domain": "Production", "indicator_code": "P2", "indicator_name": "Printing Cost Volatility", "severity": 4, "stakeholder": "Publisher", "region": "NCR", "session": "FGD1"},
    {"id": 4, "segment_id": "FGD3_012", "snippet": "Many schools have limited library facilities and students cannot easily access books.", "domain": "Access", "indicator_code": "A1", "indicator_name": "Library Infrastructure Weakness", "severity": 4, "stakeholder": "Librarian", "region": "Mindanao", "session": "FGD3"},
    {"id": 5, "segment_id": "FGD2_019", "snippet": "Authors receive unclear royalty statements and have difficulty understanding their earnings.", "domain": "Creation", "indicator_code": "C2", "indicator_name": "Royalty Transparency", "severity": 3, "stakeholder": "Author", "region": "NCR", "session": "FGD2"},
]
next_id = 6

INDICATORS = {
    "Creation": [
        {"code": "C1", "name": "Contract Fairness", "desc": "Fairness and transparency of contracts between creators and publishers"},
        {"code": "C2", "name": "Royalty Transparency", "desc": "Clarity and adequacy of royalty structures and reporting"},
        {"code": "C3", "name": "Copyright Protection", "desc": "Protection and enforcement of intellectual property rights"},
        {"code": "C4", "name": "Curriculum Volatility", "desc": "Impact of frequent curriculum changes on creative work"},
        {"code": "C5", "name": "Creator Income Stability", "desc": "Economic sustainability of authors, illustrators, and editors"},
    ],
    "Production": [
        {"code": "P1", "name": "Editorial Workflow Compression", "desc": "Time pressure and compressed editorial production cycles"},
        {"code": "P2", "name": "Printing Cost Volatility", "desc": "Rising and unpredictable printing costs"},
        {"code": "P3", "name": "Import Dependence", "desc": "Reliance on imported paper, ink, and materials"},
        {"code": "P4", "name": "Small Print Run Constraint", "desc": "High unit costs due to limited print volumes"},
        {"code": "P5", "name": "Production Quality Risk", "desc": "Quality control risks in printing and production processes"},
    ],
    "Distribution": [
        {"code": "D1", "name": "Logistics Cost Burden", "desc": "High cost of transporting books across regions"},
        {"code": "D2", "name": "Infrastructure Deficit", "desc": "Lack of warehousing and distribution infrastructure"},
        {"code": "D3", "name": "Publisher Distribution Overload", "desc": "Publishers required to manage logistics beyond core functions"},
        {"code": "D4", "name": "Regional Access Inequality", "desc": "Uneven availability of books across regions"},
        {"code": "D5", "name": "Disaster Logistics Risk", "desc": "Supply chain disruptions caused by disasters or geography"},
    ],
    "Access": [
        {"code": "A1", "name": "Library Infrastructure Weakness", "desc": "Limited public and school library capacity"},
        {"code": "A2", "name": "School Library Accessibility", "desc": "Restricted or limited student access to library collections"},
        {"code": "A3", "name": "Reading Culture Support", "desc": "Weak institutional programs promoting reading"},
        {"code": "A4", "name": "Digital Infrastructure Gap", "desc": "Uneven internet and device access affecting digital publishing"},
        {"code": "A5", "name": "Digital Market Readiness", "desc": "Low willingness or capacity to pay for digital books"},
    ],
    "Governance": [
        {"code": "G1", "name": "Procurement Policy Volatility", "desc": "Frequent changes in procurement rules and procedures"},
        {"code": "G2", "name": "Payment Delay Risk", "desc": "Delayed payments in public procurement systems"},
        {"code": "G3", "name": "Evaluation Transparency", "desc": "Lack of clear standards in textbook evaluation processes"},
        {"code": "G4", "name": "Institutional Coordination Gap", "desc": "Weak coordination among agencies governing the industry"},
    ],
}

STAKEHOLDERS = ["Publisher", "Author", "Illustrator", "Editor", "Librarian", "Distributor", "Bookseller", "Educator", "Reader", "Government"]
REGIONS = ["NCR", "CAR", "Region I", "Region II", "Region III", "Region IV-A", "Region IV-B", "Region V", "Region VI", "Region VII", "Region VIII", "Region IX", "Region X", "Region XI", "Region XII", "CARAGA", "BARMM"]
SEVERITY_LABELS = {1: "Minor Mention", 2: "Weak Constraint", 3: "Moderate Issue", 4: "Significant Structural Issue", 5: "Critical Systemic Barrier"}
DOMAIN_ORDER = ["Creation", "Production", "Distribution", "Access", "Governance"]


def compute_analytics():
    indicator_data = defaultdict(lambda: {"count": 0, "total": 0, "domain": "", "name": ""})
    domain_data = defaultdict(lambda: {"total": 0, "count": 0})
    stakeholder_data = defaultdict(lambda: {"count": 0, "total": 0})
    region_data = defaultdict(lambda: {"count": 0, "total": 0})

    for e in entries:
        code = e["indicator_code"]
        indicator_data[code]["count"] += 1
        indicator_data[code]["total"] += e["severity"]
        indicator_data[code]["domain"] = e["domain"]
        indicator_data[code]["name"] = e["indicator_name"]

        domain_data[e["domain"]]["total"] += e["severity"]
        domain_data[e["domain"]]["count"] += 1

        stakeholder_data[e["stakeholder"]]["count"] += 1
        stakeholder_data[e["stakeholder"]]["total"] += e["severity"]

        region_data[e["region"]]["count"] += 1
        region_data[e["region"]]["total"] += e["severity"]

    indicators = []
    for code, d in indicator_data.items():
        avg = round(d["total"] / d["count"], 2) if d["count"] else 0
        indicators.append({
            "code": code, "name": d["name"], "domain": d["domain"],
            "count": d["count"], "avg": avg,
            "priority": d["count"] >= 3 and avg >= 4.0,
            "pct": round((avg / 5) * 100),
        })
    indicators.sort(key=lambda x: (-x["avg"], -x["count"]))

    domains = []
    for dom in DOMAIN_ORDER:
        if dom in domain_data:
            d = domain_data[dom]
            avg = round(d["total"] / d["count"], 2)
            domains.append({"domain": dom, "avg": avg, "count": d["count"], "pct": round((avg / 5) * 100)})

    cipq_index = round(sum(d["avg"] for d in domains) / len(domains), 2) if domains else 0

    stakeholders = [{"name": k, "count": v["count"], "avg": round(v["total"] / v["count"], 2)}
                    for k, v in stakeholder_data.items()]
    stakeholders.sort(key=lambda x: -x["count"])

    regions = [{"name": k, "count": v["count"], "avg": round(v["total"] / v["count"], 2)}
               for k, v in region_data.items()]
    regions.sort(key=lambda x: -x["avg"])

    return {"indicators": indicators, "domains": domains, "cipq_index": cipq_index,
            "stakeholders": stakeholders, "regions": regions}


@app.route("/")
def index():
    domain_filter = request.args.get("domain", "All")
    filtered = entries if domain_filter == "All" else [e for e in entries if e["domain"] == domain_filter]
    analytics = compute_analytics()
    return render_template("index.html",
        entries=filtered, all_entries=entries,
        indicators=INDICATORS, stakeholders=STAKEHOLDERS, regions=REGIONS,
        severity_labels=SEVERITY_LABELS, domain_order=DOMAIN_ORDER,
        analytics=analytics, domain_filter=domain_filter,
        edit_entry=None)


@app.route("/edit/<int:entry_id>")
def edit_view(entry_id):
    entry = next((e for e in entries if e["id"] == entry_id), None)
    if not entry:
        return redirect(url_for("index"))
    analytics = compute_analytics()
    return render_template("index.html",
        entries=entries, all_entries=entries,
        indicators=INDICATORS, stakeholders=STAKEHOLDERS, regions=REGIONS,
        severity_labels=SEVERITY_LABELS, domain_order=DOMAIN_ORDER,
        analytics=analytics, domain_filter="All",
        edit_entry=entry)


@app.route("/add", methods=["POST"])
def add_entry():
    global next_id
    domain = request.form.get("domain", "Creation")
    code = request.form.get("indicator_code", "")
    ind_list = INDICATORS.get(domain, [])
    ind_name = next((i["name"] for i in ind_list if i["code"] == code), "")
    seg_id = request.form.get("segment_id", "").strip() or f"SEG{next_id:03d}"
    entries.append({
        "id": next_id,
        "segment_id": seg_id,
        "snippet": request.form.get("snippet", "").strip(),
        "domain": domain,
        "indicator_code": code,
        "indicator_name": ind_name,
        "severity": int(request.form.get("severity", 3)),
        "stakeholder": request.form.get("stakeholder", ""),
        "region": request.form.get("region", ""),
        "session": request.form.get("session", "").strip(),
    })
    next_id += 1
    return redirect(url_for("index"))


@app.route("/update/<int:entry_id>", methods=["POST"])
def update_entry(entry_id):
    entry = next((e for e in entries if e["id"] == entry_id), None)
    if entry:
        domain = request.form.get("domain", entry["domain"])
        code = request.form.get("indicator_code", "")
        ind_list = INDICATORS.get(domain, [])
        ind_name = next((i["name"] for i in ind_list if i["code"] == code), "")
        entry.update({
            "segment_id": request.form.get("segment_id", "").strip() or entry["segment_id"],
            "snippet": request.form.get("snippet", "").strip(),
            "domain": domain,
            "indicator_code": code,
            "indicator_name": ind_name,
            "severity": int(request.form.get("severity", 3)),
            "stakeholder": request.form.get("stakeholder", ""),
            "region": request.form.get("region", ""),
            "session": request.form.get("session", "").strip(),
        })
    return redirect(url_for("index"))


@app.route("/delete/<int:entry_id>", methods=["POST"])
def delete_entry(entry_id):
    global entries
    entries = [e for e in entries if e["id"] != entry_id]
    return redirect(url_for("index"))


@app.route("/api/indicators/<domain>")
def api_indicators(domain):
    return jsonify(INDICATORS.get(domain, []))


@app.route("/analytics")
def analytics_view():
    analytics = compute_analytics()
    return render_template("analytics.html",
        analytics=analytics, domain_order=DOMAIN_ORDER,
        entries=entries, severity_labels=SEVERITY_LABELS)


if __name__ == "__main__":
    app.run(debug=True, port=5050)


@app.route("/api/suggest-severity", methods=["POST"])
def suggest_severity():
    data = request.get_json()
    snippet        = (data.get("snippet") or "").strip()
    domain         = (data.get("domain") or "").strip()
    indicator_name = (data.get("indicator_name") or "").strip()

    if not snippet:
        return jsonify({"error": "No snippet provided."}), 400

    system_prompt = (
        "You are an expert qualitative policy researcher specializing in the Philippine book "
        "publishing industry. You apply the CIPQ (Creative Industry Policy Quadrant) severity "
        "scoring rubric strictly and consistently.\n\n"
        "SEVERITY SCALE:\n"
        "1 - Minor Mention: Issue raised briefly, no significant impact described.\n"
        "2 - Weak Constraint: Issue is present but limited in scope or consequence.\n"
        "3 - Moderate Issue: Recurrent issue that affects operations in noticeable ways.\n"
        "4 - Significant Structural Issue: Imposes serious operational challenges for stakeholders.\n"
        "5 - Critical Systemic Barrier: Major structural constraint affecting the entire sector.\n\n"
        "SCORING CRITERIA:\n"
        "- Operational impact: Does it describe direct disruptions (delays, cost spikes, shutdowns)?\n"
        "- Breadth: Does it affect many stakeholders or a wide geographic area?\n"
        "- Systemic consequences: Long-term, sector-wide or institutional problems signal higher severity.\n"
        "- Urgency / intensity: Strong language ('impossible', 'critical', 'collapsed') signals higher severity.\n\n"
        "Respond ONLY with a valid JSON object. No markdown, no extra text:\n"
        '{"score": <integer 1-5>, "rationale": "<one concise sentence>", "key_factors": ["<factor 1>", "<factor 2>", "<factor 3>"]}'
    )

    user_prompt = (
        f'Score the severity of this narrative segment from a Philippine book publishing stakeholder:\n\n'
        f'SNIPPET: "{snippet}"\n'
        f'CIPQ DOMAIN: {domain}\n'
        f'INDICATOR: {indicator_name}\n\n'
        f'Apply the rubric and return JSON only.'
    )

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return jsonify({"error": "ANTHROPIC_API_KEY environment variable is not set."}), 500

    try:
        payload = json.dumps({
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 300,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}]
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            result = json.loads(resp.read().decode("utf-8"))

        text = result["content"][0]["text"].strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        parsed = json.loads(text.strip())
        return jsonify(parsed)

    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return jsonify({"error": f"Anthropic API error {e.code}: {body}"}), 502
    except Exception as e:
        return jsonify({"error": str(e)}), 500
