
from model import analyze_opportunity
from tool import prepare_evidence


def read_document(number, default_title=""):
    print(f"\n--- Document {number} ---")

    title = input(
        f"Document name [{default_title or 'Untitled'}]: "
    ).strip()

    if not title:
        title = default_title or f"Document {number}"

    print("Paste the document text.")
    print("Type END on its own line when finished.")

    lines = []

    while True:
        try:
            line = input()
        except EOFError:
            break

        if line.strip() == "END":
            break

        lines.append(line)

    return {
        "id": number,
        "title": title,
        "content": "\n".join(lines).strip()
    }


def print_list(title, items):
    print(f"\n{title}")

    if not items:
        print("- None reported.")
        return

    for item in items:
        if isinstance(item, dict):
            print(f"- {item.get('category', 'Finding')}")
            print(f"  Severity: {item.get('severity', 'Info')}")
            print(f"  Details: {item.get('details', '')}")

            for quote in item.get("evidence", []):
                print(f"  Evidence: {quote}")

            print(
                "  Recommendation:",
                item.get("recommendation", "")
            )
        else:
            print(f"- {item}")


def main():
    print("=" * 48)
    print("          OPPORTUNITYSHIELD")
    print(" Internship and Job Opportunity Risk Checker")
    print("=" * 48)

    print("\n1. Verify one internship email or message")
    print("2. Compare multiple documents")

    choice = input("\nChoose mode (1/2): ").strip()

    if choice == "1":
        documents = [read_document(1, "Internship message")]

    elif choice == "2":
        documents = []
        number = 1

        while True:
            document = read_document(number)
            documents.append(document)
            number += 1

            if number > 10:
                print("Maximum of 10 documents reached.")
                break

            answer = input(
                "\nAdd another document? (y/n): "
            ).strip().lower()

            if answer != "y":
                break

    else:
        print("Invalid choice. Run the program again.")
        return

    print("\n--- Optional identity details ---")
    print("Enter details only if you have them.")

    company_domain = input(
        "Expected official company domain (or Enter to skip): "
    ).strip()

    recruiter_email = input(
        "Recruiter email address (or Enter to skip): "
    ).strip()

    answer = input(
        "\nDo you have text copied from an official company "
        "website or internship posting? (y/n): "
    ).strip().lower()

    if answer == "y":
        source = read_document(
            len(documents) + 1,
            "Official-source excerpt (user supplied)"
        )

        if source["content"]:
            documents.append(source)

    try:
        evidence = prepare_evidence(
            documents,
            official_domain=company_domain,
            recruiter_email=recruiter_email
        )
    except ValueError as error:
        print(f"\nInput error: {error}")
        return

    print("\n--- Preliminary local checks ---")

    if evidence["local_signals"]:
        for signal in evidence["local_signals"]:
            print(f"\n- {signal['category']}")
            print(f"  {signal['details']}")

            for item in signal.get("evidence", []):
                print(f"  Evidence: {item}")

            print(
                "  Recommendation:",
                signal["recommendation"]
            )
    else:
        print("No configured warning patterns were detected.")

    print("\n--- Document comparison checks ---")

    if evidence["comparison_findings"]:
        for finding in evidence["comparison_findings"]:
            print(f"\n- {finding['category']}")
            print(f"  {finding['details']}")

            for item in finding["evidence"]:
                print(f"  Evidence: {item}")
    elif len(documents) < 2:
        print("Only one document was supplied; no cross-document "
              "comparison is possible.")
    else:
        print("No conflicts detected by the basic text matcher.")

    print("\n--- Preliminary risk assessment ---")
    print(f"Score: {evidence['risk_score']}/100")
    print(f"Level: {evidence['risk_level']}")
    print("This is a heuristic score, not a fraud probability.")

    for reason in evidence["risk_score_explanation"]:
        print("-", reason)

    print("\n--- Local AI analysis ---")
    print("Analyzing with Ollama. Please wait...\n")

    report = analyze_opportunity(evidence)

    print("=" * 48)
    print("              FINAL REPORT")
    print("=" * 48)

    print("\nSummary:")
    print(report.get("summary", "No summary available."))

    print("\nPreliminary risk score:",
          f"{report.get('risk_score', 0)}/100")

    print("Preliminary risk level:",
          report.get("preliminary_risk_level", "Unknown"))

    print("AI assessment:",
          report.get("risk_level", "Insufficient Evidence"))

    print("\nScore explanation:")
    print(report.get("score_explanation", ""))

    print_list("Findings:", report.get("findings", []))
    print_list("Matching details:", report.get("matching_details", []))
    print_list("Questions to ask:", report.get("questions_to_ask", []))
    print_list("Recommended next steps:", report.get("next_steps", []))
    print_list("Limitations:", report.get("limitations", []))

    print("\nVerification status:")
    print(report.get(
        "verification_status",
        "Not independently verified"
    ))

    print("\nImportant safety advice:")
    print("- Do not pay a fee just to test an opportunity.")
    print("- Never share OTPs, UPI PINs, passwords, or CVVs.")
    print("- Contact the employer using independently obtained "
          "official contact details.")
    print("- This program does not independently authenticate "
          "companies, websites, or recruiters.")

    print("\nAnalysis complete.")


if __name__ == "__main__":
    main()
