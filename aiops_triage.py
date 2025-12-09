import re
import json
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Dict

from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline


LOG_PATH = "logs.txt"
GEN_MODEL_NAME = "google/flan-t5-base"

# --- PHASE 2: Knowledge Base (Mini-RAG) ---
# In a real system, this would be a vector DB (Chroma/Pinecone).
# Here, we use a simple keyword-based lookup for demonstration.
KNOWLEDGE_BASE = {
    "database connection timeout": "RUNBOOK-DB-001: Check RDS CPU utilization. If > 80%, scale up read replicas. If normal, check VPC security groups.",
    "payment gateway timeout": "RUNBOOK-PAY-99: Verify Stripe API status page. If Stripe is up, check internal NAT gateway latency.",
    "token signature validation": "RUNBOOK-AUTH-55: Rotate JWT public keys. Check if client clock skew > 5 minutes.",
    "slow response": "RUNBOOK-PERF-12: Check Redis cache hit rate. If < 50%, flush cache or increase memory."
}


@dataclass
class LogEntry:
    timestamp: str
    service: str
    level: str
    message: str


def parse_log_line(line: str) -> LogEntry | None:
    line = line.strip()
    if not line:
        return None
    m = re.match(r"^(\S+)\s+\[([^\]]+)\]\s+(\w+):\s+(.*)$", line)
    if not m:
        return None
    timestamp, service, level, message = m.groups()
    return LogEntry(timestamp=timestamp, service=service, level=level, message=message)


def load_logs(path: str) -> List[LogEntry]:
    entries: List[LogEntry] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                entry = parse_log_line(line)
                if entry:
                    entries.append(entry)
    except FileNotFoundError:
        print(f"Error: {path} not found.")
    return entries


def derive_incident_key(entry: LogEntry) -> str:
    normalized_msg = re.sub(r"\d+", "<NUM>", entry.message.lower())
    normalized_msg = re.sub(r"\s+", " ", normalized_msg).strip()
    key = f"{entry.service}::{normalized_msg}"
    return key


def group_incidents(entries: List[LogEntry]) -> Dict[str, List[LogEntry]]:
    groups: Dict[str, List[LogEntry]] = defaultdict(list)
    for e in entries:
        if e.level not in {"ERROR", "WARN"}:
            continue
        key = derive_incident_key(e)
        groups[key].append(e)
    return groups


def retrieve_runbook(pattern: str) -> str:
    """Simulates RAG retrieval."""
    for keyword, runbook in KNOWLEDGE_BASE.items():
        if keyword in pattern:
            return runbook
    return "No specific runbook found. Follow general triage SOP."




def build_summary_prompt(incident_key: str, entries: List[LogEntry]) -> str:
    service, pattern = incident_key.split("::", 1)
    logs_text = "\n".join(f"{e.timestamp} [{e.level}] {e.message}" for e in entries[-5:])
    runbook_context = retrieve_runbook(pattern)

    prompt = f"""
Given the logs, output a triage report.

[EXAMPLE]
Input Logs: 2024-01-01 [orders] ERROR connection timed out
Runbook context: Check DB.
Report:
Summary: Database connection failing intermittently.
Severity: P2
Root Cause: High database load or network partition.
Action Items: Check RDS CPU, Investigate VPC logs

[TARGET]
Input Logs:
{logs_text}
Runbook context: {runbook_context}
Report:
""".strip()
    return prompt

def parse_llm_output_to_json(text: str) -> Dict:
    """Parses LLM output using Regex to handle loose formatting."""
    data = {
        "summary": "N/A",
        "severity": "P3",
        "root_cause": "N/A",
        "action_items": []
    }
    
    # Regex to find fields even if they are on the same line
    # Looks for "Summary: ... Severity:" structure
    summary_match = re.search(r"Summary:\s*(.*?)(?=\s*Severity:|$)", text, re.IGNORECASE | re.DOTALL)
    severity_match = re.search(r"Severity:\s*(P\d)(?=\s*Root Cause:|$)", text, re.IGNORECASE)
    root_cause_match = re.search(r"Root Cause:\s*(.*?)(?=\s*Action Items:|$)", text, re.IGNORECASE | re.DOTALL)
    actions_match = re.search(r"Action Items:\s*(.*)", text, re.IGNORECASE | re.DOTALL)

    if summary_match:
        data["summary"] = summary_match.group(1).strip()
    if severity_match:
        data["severity"] = severity_match.group(1).strip()
    if root_cause_match:
        data["root_cause"] = root_cause_match.group(1).strip()
    
    if actions_match:
        raw_actions = actions_match.group(1).strip()
        # Remove [TARGET] or other prompt artifacts if present
        raw_actions = raw_actions.replace("[TARGET]", "").strip()
        data["action_items"] = [a.strip() for a in raw_actions.split(',') if a.strip()]

    return data

def main():
    print("Loading logs...")
    entries = load_logs(LOG_PATH)
    if not entries:
        return

    print(f"Total parsed log entries: {len(entries)}")
    groups = group_incidents(entries)
    print(f"Total incident groups: {len(groups)}")

    print("Loading generation model...")
    gen_pipe = pipeline(
        "text2text-generation",
        model=GEN_MODEL_NAME,
        tokenizer=GEN_MODEL_NAME,
        max_length=512,
    )

    print("\n=== AI Ops Enterprise Triage Report (Phase 2) ===\n")
    
    for i, (incident_key, incident_entries) in enumerate(groups.items(), start=1):
        service = incident_entries[0].service
        count = len(incident_entries)
        
        print(f"--- Incident #{i} [{service}] ({count} events) ---")
        
        prompt = build_summary_prompt(incident_key, incident_entries)
        result = gen_pipe(prompt)[0]["generated_text"].strip()
        
        # Robust parsing
        structured_data = parse_llm_output_to_json(result)
        
        # Print valid JSON
        print(json.dumps(structured_data, indent=2))
        print("\n")

if __name__ == "__main__":
    main()
