
import re
from urllib.parse import urlparse

MAX_DOCUMENT_CHARS = 12000
MAX_TOTAL_CHARS = 30000
MAX_DOCUMENTS = 10


def normalize_domain(value):
    """Normalize a domain or website URL for comparison."""
    value = (value or "").strip().lower()

    if not value:
        return ""

    if "://" not in value:
        value = "https://" + value

    try:
        parsed = urlparse(value)

        if parsed.scheme not in ("http", "https"):
            return ""

        host = (parsed.hostname or "").strip(".").lower()

        if not host or "." not in host:
            return ""

        return host
    except ValueError:
        return ""


def prepare_evidence(documents, official_domain="", recruiter_email=""):
    if not isinstance(documents, list) or not documents:
        raise ValueError("Provide at least one document.")

    if len(documents) > MAX_DOCUMENTS:
        raise ValueError(f"Maximum {MAX_DOCUMENTS} documents allowed.")

    cleaned = []
    total = 0

    for index, document in enumerate(documents, start=1):
        if not isinstance(document, dict):
            raise ValueError(f"Document {index} is invalid.")

        title = str(document.get("title", "")).strip()
        content = str(document.get("content", "")).strip()

        if not title or not content:
            raise ValueError(
                f"Document {index} needs a title and text."
            )

        if len(content) > MAX_DOCUMENT_CHARS:
            raise ValueError(
                f"{title} exceeds {MAX_DOCUMENT_CHARS} characters."
            )

        total += len(content)

        cleaned.append({
            "id": document.get("id", index),
            "title": title,
            "content": content
        })

    if total > MAX_TOTAL_CHARS:
        raise ValueError(
            f"Combined text exceeds {MAX_TOTAL_CHARS} characters."
        )

    domain = normalize_domain(official_domain)
    email = (recruiter_email or "").strip().lower()
    email_domain = ""

    if email and re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        email_domain = email.rsplit("@", 1)[1]

    evidence = {
        "documents": cleaned,
        "official_domain": domain,
        "recruiter_email": email,
        "local_signals": [],
        "comparison_findings": [],
        "matching_details": [],
        "risk_score": 0,
        "risk_level": "Insufficient Evidence",
        "risk_score_explanation": [],
        "source_status": (
            "User-supplied source details; not independently authenticated."
        )
    }

    if domain and email_domain and email_domain != domain:
        evidence["local_signals"].append({
            "category": "Recruiter identity",
            "severity": "Warning",
            "details": (
                "The recruiter email domain differs from the supplied "
                "company domain. Some legitimate recruiters use other "
                "domains, so verify independently."
            ),
            "evidence": [
                f"Supplied company domain: {domain}",
                f"Recruiter email domain: {email_domain}"
            ],
            "recommendation": (
                "Confirm the recruiter through contact details obtained "
                "independently from the company's official website."
            ),
            "points": 15
        })

    evidence["local_signals"].extend(local_red_flags(cleaned))
    comparison = compare_documents(cleaned)

    evidence["comparison_findings"] = comparison["conflicts"]
    evidence["matching_details"] = comparison["matches"]

    score = 0
    reasons = []

    for signal in evidence["local_signals"]:
        points = signal.get("points", 0)
        score += points
        reasons.append(f"+{points}: {signal['category']}")

    for conflict in evidence["comparison_findings"]:
        points = conflict.get("points", 0)
        score += points
        reasons.append(f"+{points}: {conflict['category']} conflict")

    score = min(score, 100)

    if not cleaned or all(not d["content"] for d in cleaned):
        level = "Insufficient Evidence"
    elif score >= 60:
        level = "High"
    elif score >= 25:
        level = "Medium"
    elif score > 0:
        level = "Low"
    else:
        level = "No major warning signals detected"

    evidence["risk_score"] = score
    evidence["risk_level"] = level
    evidence["risk_score_explanation"] = reasons

    return evidence


def local_red_flags(documents):
    """Detect warning signals without treating them as proof of fraud."""
    rules = [
        (
            r"\b(registration|activation|processing|security|"
            r"placement|training)\s+fee\b|"
            r"\b(pay\s+(?:to\s+join|to\s+get\s+(?:the\s+)?job)|"
            r"upfront\s+payment)\b",
            "Upfront fee or payment request",
            35,
            "Do not pay before independently verifying the opportunity."
        ),
        (
            r"\b(?:share|send|provide|tell us)\b.{0,60}"
            r"\b(?:otp|upi pin|bank password|cvv)\b|"
            r"\b(?:otp|upi pin|bank password|cvv)\b",
            "Sensitive authentication or payment information",
            50,
            "Never share OTPs, UPI PINs, bank passwords, or CVVs."
        ),
        (
            r"\b(?:guaranteed job|100%\s+placement|"
            r"guaranteed internship|guaranteed selection)\b",
            "Guaranteed job or selection claim",
            15,
            "Ask for written terms and verify the claim independently."
        ),
        (
            r"\b(?:urgent|today only|act now|limited seats|"
            r"immediate payment|offer expires in \d+ hours)\b",
            "Pressure or urgency language",
            10,
            "Take time to verify before sharing information or paying."
        ),
        (
            r"\b(?:no interview|without interview)\b.{0,60}"
            r"\b(?:guaranteed|confirmed|selection|job|internship)\b",
            "Selection promised without an interview",
            15,
            "Confirm the selection process with the employer."
        )
    ]

    results = []

    for document in documents:
        content = document["content"]

        for pattern, category, points, recommendation in rules:
            if re.search(pattern, content, re.IGNORECASE):
                results.append({
                    "category": category,
                    "severity": (
                        "High" if points >= 35
                        else "Warning"
                    ),
                    "details": (
                        f"A potential warning signal appears in "
                        f"{document['title']}."
                    ),
                    "evidence": [
                        f"Document {document['id']}: {category}"
                    ],
                    "recommendation": recommendation,
                    "points": points
                })

    return results


def compare_documents(documents):
    """Compare common opportunity details using simple text patterns."""
    fields = {
        "Stipend or salary": (
            r"(?:stipend|salary|pay|compensation)"
            r"\s*(?:amount)?\s*[:=-]?\s*"
            r"(?:rs\.?|inr|₹)?\s*[\d,]+"
            r"(?:\.\d+)?\s*(?:per\s+month|/\s*month|monthly)?"
        ),
        "Duration": (
            r"(?:duration|period|tenure)\s*[:=-]?\s*"
            r"\d+\s*(?:days?|weeks?|months?|years?)"
        ),
        "Registration fee": (
            r"(?:registration|processing|training|activation)"
            r"\s+fee\s*[:=-]?\s*(?:rs\.?|inr|₹)?\s*[\d,]+"
        ),
        "Work arrangement": (
            r"\b(?:remote|hybrid|onsite|on-site|work from home)\b"
        )
    }

    extracted = {}
    conflicts = []
    matches = []

    for field, pattern in fields.items():
        values = []

        for document in documents:
            found = re.findall(
                pattern, document["content"], re.IGNORECASE
            )

            for value in found:
                normalized = re.sub(r"\s+", " ", value.strip().lower())
                values.append({
                    "document": document["title"],
                    "id": document["id"],
                    "value": normalized
                })

        extracted[field] = values

        distinct = {item["value"] for item in values}

        if len(distinct) > 1:
            conflicts.append({
                "category": field,
                "severity": "Warning",
                "details": (
                    f"Different {field.lower()} values were found. "
                    "Check the exact quoted text before concluding "
                    "that the documents contradict each other."
                ),
                "evidence": [
                    f"Document {item['id']} ({item['document']}): "
                    f"{item['value']}"
                    for item in values
                ],
                "recommendation": (
                    f"Ask the employer to confirm the correct {field.lower()} "
                    "in writing."
                ),
                "points": 20
            })
        elif len(values) >= 2:
            matches.append(
                f"{field}: the extracted values match across documents."
            )

    return {
        "extracted_claims": extracted,
        "conflicts": conflicts,
        "matches": matches
    }
