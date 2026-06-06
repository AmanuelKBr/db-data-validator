import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import requests
from utils.models import TableValidationReport, BatchValidationReport
from typing import List, Optional, Generator

_SYSTEM_PROMPT = """You are DataDoctor, an expert data quality analyst AI assistant. Your role is to:
1. Analyze validation failures and identify root causes
2. Provide actionable insights for data engineers
3. Suggest business or technical remedies
4. Explain patterns in data quality issues

Be concise, professional, and focus on practical solutions. Use clear language that both technical and non-technical stakeholders can understand.

Format your response as:
**Key Issues:** (2-3 main problems identified)
**Root Causes:** (why these issues likely occurred)
**Recommendations:** (specific actions to take)
**Priority:** (which issues to fix first)"""

_FOLLOWUP_SYSTEM = (
    "You are DataDoctor, an expert data quality analyst. "
    "Answer follow-up questions about validation results with practical insights."
)


class DataDoctor:
    """AI-powered data quality insights. Routes between Ollama (local) and Groq backends."""

    GROQ_MODELS = [
        "llama-3.1-8b-instant",               # fastest free tier
        "llama-3.3-70b-versatile",             # most capable free tier
        "meta-llama/llama-4-scout-17b-16e-instruct",  # Llama 4
        "qwen/qwen3-32b",                      # Qwen 3
    ]

    def __init__(
        self,
        backend: str = "ollama",
        model: Optional[str] = None,
        groq_api_key: Optional[str] = None,
        ollama_url: str = "http://localhost:11434",
    ):
        if backend not in ("ollama", "groq"):
            raise ValueError(f"Unknown backend '{backend}'. Choose 'ollama' or 'groq'.")

        self.backend = backend
        self.ollama_url = ollama_url.rstrip("/")
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY", "")
        self.conversation_history: List[dict] = []

        if backend == "ollama":
            self.model = model or "llama3"
        else:
            self.model = model or self.GROQ_MODELS[0]

    # ── availability checks ────────────────────────────────────────────────────

    def check_availability(self) -> tuple:
        """Returns (is_available: bool, message: str)."""
        return self._check_ollama() if self.backend == "ollama" else self._check_groq()

    def _check_ollama(self) -> tuple:
        try:
            resp = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", [])]
                if not models:
                    return False, "Ollama is running but no models installed. Run: ollama pull llama3"
                return True, f"Ollama ready — {len(models)} model(s) installed"
            return False, f"Ollama returned HTTP {resp.status_code}"
        except requests.exceptions.ConnectionError:
            return False, "Ollama not reachable. Start it with: ollama serve"
        except Exception as e:
            return False, f"Ollama check failed: {e}"

    def _check_groq(self) -> tuple:
        if not self.groq_api_key:
            return False, "GROQ_API_KEY not set. Add it to .env or enter it in the sidebar."
        try:
            headers = {"Authorization": f"Bearer {self.groq_api_key}"}
            resp = requests.get(
                "https://api.groq.com/openai/v1/models", headers=headers, timeout=10
            )
            if resp.status_code == 200:
                return True, "Groq API connected"
            if resp.status_code == 401:
                return False, "Groq API key is invalid"
            return False, f"Groq returned HTTP {resp.status_code}"
        except Exception as e:
            return False, f"Groq check failed: {e}"

    def get_ollama_models(self) -> List[str]:
        """Return installed Ollama model names, empty list if unreachable."""
        try:
            resp = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if resp.status_code == 200:
                return [m["name"] for m in resp.json().get("models", [])]
        except Exception:
            pass
        return []

    # ── streaming generators ───────────────────────────────────────────────────

    def _stream_ollama(
        self, messages: List[dict], system_prompt: str, max_tokens: int
    ) -> Generator[str, None, None]:
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system_prompt}] + messages,
            "stream": True,
            "options": {"num_predict": max_tokens},
        }
        with requests.post(
            f"{self.ollama_url}/api/chat", json=payload, stream=True, timeout=300
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if line:
                    chunk = json.loads(line)
                    if not chunk.get("done"):
                        yield chunk["message"]["content"]

    def _stream_groq(
        self, messages: List[dict], system_prompt: str, max_tokens: int
    ) -> Generator[str, None, None]:
        if not self.groq_api_key:
            raise ValueError("GROQ_API_KEY is not set.")
        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system_prompt}] + messages,
            "max_tokens": max_tokens,
            "stream": True,
        }
        with requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            stream=True,
            timeout=60,
        ) as resp:
            if not resp.ok:
                try:
                    body = resp.json()
                    detail = body.get("error", {}).get("message", resp.text[:300])
                except Exception:
                    detail = resp.text[:300]
                raise requests.HTTPError(
                    f"Groq {resp.status_code}: {detail}", response=resp
                )
            for line in resp.iter_lines():
                if line and line.startswith(b"data: "):
                    data = line[6:]
                    if data == b"[DONE]":
                        break
                    chunk = json.loads(data)
                    delta = chunk["choices"][0]["delta"].get("content", "")
                    if delta:
                        yield delta

    def _stream_llm(
        self, messages: List[dict], system_prompt: str, max_tokens: int = 1000
    ) -> Generator[str, None, None]:
        if self.backend == "ollama":
            yield from self._stream_ollama(messages, system_prompt, max_tokens)
        else:
            yield from self._stream_groq(messages, system_prompt, max_tokens)

    # ── non-streaming fallbacks (kept for programmatic use) ───────────────────

    def _call_ollama(self, messages: List[dict], system_prompt: str, max_tokens: int) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system_prompt}] + messages,
            "stream": False,
            "options": {"num_predict": max_tokens},
        }
        resp = requests.post(f"{self.ollama_url}/api/chat", json=payload, timeout=300)
        resp.raise_for_status()
        return resp.json()["message"]["content"]

    def _call_groq(self, messages: List[dict], system_prompt: str, max_tokens: int) -> str:
        if not self.groq_api_key:
            raise ValueError("GROQ_API_KEY is not set.")
        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system_prompt}] + messages,
            "max_tokens": max_tokens,
        }
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    # ── public API ────────────────────────────────────────────────────────────

    def stream_analysis(self, report: TableValidationReport) -> Generator[str, None, None]:
        """
        Streaming generator for validation report analysis.
        Use with st.write_stream() — yields chunks, adds full response to history.
        """
        context = self._build_report_context(report)
        user_message = (
            f"Please analyze this data validation report and provide insights:\n\n"
            f"{context}\n\n"
            "Focus on:\n"
            "1. What patterns do you see?\n"
            "2. What likely caused these issues?\n"
            "3. What should we fix first?\n"
            "4. Any quick wins we can implement?"
        )
        self.conversation_history.append({"role": "user", "content": user_message})

        full_response: List[str] = []
        try:
            for chunk in self._stream_llm(self.conversation_history, _SYSTEM_PROMPT, 1000):
                full_response.append(chunk)
                yield chunk
        except Exception as e:
            error_msg = f"\n\n⚠️ DataDoctor error ({self.backend}/{self.model}): {e}"
            full_response.append(error_msg)
            yield error_msg

        self.conversation_history.append(
            {"role": "assistant", "content": "".join(full_response)}
        )

    def stream_followup(self, question: str) -> Generator[str, None, None]:
        """Streaming generator for follow-up questions. Use with st.write_stream()."""
        if not self.conversation_history:
            yield "Please run a validation first so DataDoctor can analyze the results."
            return

        self.conversation_history.append({"role": "user", "content": question})
        full_response: List[str] = []
        try:
            for chunk in self._stream_llm(self.conversation_history, _FOLLOWUP_SYSTEM, 600):
                full_response.append(chunk)
                yield chunk
        except Exception as e:
            error_msg = f"\n\n⚠️ DataDoctor error ({self.backend}/{self.model}): {e}"
            full_response.append(error_msg)
            yield error_msg

        self.conversation_history.append(
            {"role": "assistant", "content": "".join(full_response)}
        )

    def ask_followup(self, question: str) -> str:
        """Non-streaming fallback (kept for programmatic use)."""
        if not self.conversation_history:
            return "Please run a validation first so DataDoctor can analyze the results."
        self.conversation_history.append({"role": "user", "content": question})
        try:
            if self.backend == "ollama":
                response = self._call_ollama(self.conversation_history, _FOLLOWUP_SYSTEM, 600)
            else:
                response = self._call_groq(self.conversation_history, _FOLLOWUP_SYSTEM, 600)
            self.conversation_history.append({"role": "assistant", "content": response})
            return response
        except Exception as e:
            return f"DataDoctor error ({self.backend}/{self.model}): {e}"

    def stream_batch_analysis(self, batch_report: BatchValidationReport) -> Generator[str, None, None]:
        """
        Streaming generator that analyses ALL tables in a batch report.
        Builds a compact multi-table context so the LLM understands the full picture.
        """
        context = self._build_batch_context(batch_report)
        user_message = (
            f"Please analyse this multi-table data validation report and provide insights:\n\n"
            f"{context}\n\n"
            "For each table:\n"
            "1. What are the most critical issues?\n"
            "2. Are there cross-table patterns (same rule failing across multiple tables)?\n"
            "3. What should the team fix first — prioritise by business impact?\n"
            "4. Any quick wins that apply across all tables?"
        )
        self.conversation_history.append({"role": "user", "content": user_message})
        full_response: List[str] = []
        try:
            for chunk in self._stream_llm(self.conversation_history, _SYSTEM_PROMPT, 1200):
                full_response.append(chunk)
                yield chunk
        except Exception as e:
            error_msg = f"\n\n⚠️ DataDoctor error ({self.backend}/{self.model}): {e}"
            full_response.append(error_msg)
            yield error_msg
        self.conversation_history.append(
            {"role": "assistant", "content": "".join(full_response)}
        )

    def reset_conversation(self):
        self.conversation_history = []

    # ── context builder ───────────────────────────────────────────────────────

    def _build_batch_context(self, batch_report: BatchValidationReport, max_tables: int = 8, max_issues_per_table: int = 6) -> str:
        """Compact multi-table context — stays within token budget."""
        lines = [
            "**Batch Validation Report**",
            f"**Tables validated:** {batch_report.total_tables}  |  "
            f"**Total issues:** {batch_report.total_issues}  |  "
            f"Critical: {batch_report.get_critical_count()}  "
            f"Warning: {batch_report.get_warning_count()}  "
            f"Info: {batch_report.get_info_count()}",
            "",
        ]
        for t_report in batch_report.table_reports[:max_tables]:
            n = len(t_report.results)
            if n == 0:
                lines.append(f"✅ **{t_report.table_name}** — no issues ({t_report.total_rows_checked:,} rows)")
                continue
            crit = sum(1 for r in t_report.results if r.severity.value == "CRITICAL")
            lines.append(f"\n**{t_report.table_name}** — {t_report.total_rows_checked:,} rows, {n} issue(s) (🔴 {crit} critical)")
            prioritised = sorted(t_report.results, key=lambda r: (0 if r.severity.value=="CRITICAL" else 1 if r.severity.value=="WARNING" else 2, -r.total_failures))
            for r in prioritised[:max_issues_per_table]:
                lines.append(f"  • [{r.severity.value}] {r.rule_name} | {r.column_name} → {r.total_failures:,} failures ({r.failure_percentage:.1f}%)")
            if n > max_issues_per_table:
                lines.append(f"  … and {n - max_issues_per_table} more issues")
        if len(batch_report.table_reports) > max_tables:
            lines.append(f"\n_(Showing {max_tables} of {len(batch_report.table_reports)} tables — prioritised by severity)_")
        return "\n".join(lines)

    def _build_report_context(self, report: TableValidationReport, max_issues: int = 15) -> str:
        """Build a compact prompt context — caps at max_issues to keep prompts short."""
        lines = [
            f"**Table:** {report.table_name}",
            f"**Total Rows Checked:** {report.total_rows_checked:,}",
            f"**Total Issues Found:** {len(report.results)}",
            "",
        ]

        if not report.results:
            lines.append("Status: No validation issues detected — data quality is excellent!")
            return "\n".join(lines)

        critical = [r for r in report.results if r.severity.value == "CRITICAL"]
        warning  = [r for r in report.results if r.severity.value == "WARNING"]
        info     = [r for r in report.results if r.severity.value == "INFO"]

        lines += [
            f"**Critical Issues:** {len(critical)}",
            f"**Warning Issues:** {len(warning)}",
            f"**Info Issues:** {len(info)}",
            "",
            "**Validation Details:**",
        ]

        # Prioritise CRITICAL → WARNING → INFO; trim to keep prompt size manageable
        prioritized = critical + warning + info
        shown = prioritized[:max_issues]
        if len(prioritized) > max_issues:
            lines.append(
                f"_(Showing top {max_issues} of {len(prioritized)} issues, "
                "prioritised by severity)_"
            )

        for label, emoji, group in [
            ("CRITICAL", "🔴", [r for r in shown if r.severity.value == "CRITICAL"]),
            ("WARNING",  "🟡", [r for r in shown if r.severity.value == "WARNING"]),
            ("INFO",     "🔵", [r for r in shown if r.severity.value == "INFO"]),
        ]:
            if group:
                lines.append(f"\n{emoji} {label}:")
                for result in group:
                    lines.append(f"  • {result.rule_name} | Column: {result.column_name}")
                    lines.append(f"    Failures: {result.total_failures} ({result.failure_percentage:.1f}%)")

        return "\n".join(lines)
