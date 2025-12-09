
---

## 📁 `aiops_triage/README.md`

```markdown
# AI Ops Incident Triage & Summarization Engine

This project is an **AI Ops–style incident triage engine** that parses production-like logs, clusters recurring failure patterns, and uses an **LLM (Flan-T5)** to generate **structured incident reports** with severity, likely root cause, and recommended actions.

> Goal: Show how LLMs can sit on top of traditional logs and help SRE/DevOps teams make sense of noisy incidents faster.

---

## ✨ Features

- 📜 **Log Parsing**  
  - Reads plain-text logs from `logs.txt`  
  - Extracts:
    - Timestamp  
    - Service name  
    - Log level (ERROR/WARN/etc.)  
    - Message body  

- 🧩 **Incident Grouping**  
  - Groups logs into incidents by:
    - Service  
    - Normalized message pattern (numbers replaced with `<NUM>`, whitespace normalized)  
  - Focuses on `ERROR` and `WARN` events  

- 🧠 **LLM-Powered Incident Reports**  
  - Uses `google/flan-t5-base` via Hugging Face `pipeline`  
  - For each incident group, generates a structured report:
    - **Summary**  
    - **Likely root cause**  
    - **Recommended actions**  

- 📈 **Operational Insight**  
  - Shows:
    - Number of occurrences per incident  
    - Time window (first → last timestamp)  
    - Services and levels involved  
  - Helps compress low-level logs into higher-level incident narratives  

---

## 🏗️ Architecture (High Level)

```text
logs.txt
   │
   ▼
[Parsing]
   │  (timestamp, service, level, message)
   ▼
[Incident Grouping by Service + Pattern]
   │
   ▼
[Prompt Builder]
   │
   ▼
[LLM (Flan-T5) via HF Pipeline]
   │
   ▼
[Incident Report: summary, likely root cause, recommended actions]
