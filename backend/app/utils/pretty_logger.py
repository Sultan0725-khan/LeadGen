import json
import logging
from typing import Any, Dict, Optional

# ANSI colors
BLUE = "\033[94m"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"

logger = logging.getLogger(__name__)

class PrettyLogger:
    @staticmethod
    def log_request(service: str, method: str, url: str, payload: Optional[Dict[str, Any]] = None):
        """Log an outgoing request with styling."""
        print(f"\n{BOLD}{BLUE}┌─── OUTGOING REQUEST: {service} {'─' * (40 - len(service))}──┐{RESET}")
        print(f"{BOLD}{BLUE}│{RESET} {BOLD}Method:{RESET} {method}")
        print(f"{BOLD}{BLUE}│{RESET} {BOLD}URL:   {RESET} {url}")

        if payload:
            print(f"{BOLD}{BLUE}│{RESET} {BOLD}Payload:{RESET}")
            try:
                # Try to redact sensitive info if present
                safe_payload = payload.copy()
                if "password" in safe_payload: safe_payload["password"] = "********"
                if "client_secret" in safe_payload: safe_payload["client_secret"] = "********"
                if "access_token" in safe_payload: safe_payload["access_token"] = "********"

                formatted_json = json.dumps(safe_payload, indent=2)
                for line in formatted_json.split("\n"):
                    print(f"{BOLD}{BLUE}│{RESET}   {line}")
            except:
                print(f"{BOLD}{BLUE}│{RESET}   {payload}")

        print(f"{BOLD}{BLUE}└{'─' * 61}┘{RESET}")

    @staticmethod
    def log_response(service: str, status_code: int, body: Any):
        """Log an incoming response with styling."""
        color = GREEN if 200 <= status_code < 300 else RED

        print(f"\n{BOLD}{color}┌─── INCOMING RESPONSE: {service} {'─' * (40 - len(service))}──┐{RESET}")
        print(f"{BOLD}{color}│{RESET} {BOLD}Status:{RESET} {status_code}")

        if body:
            print(f"{BOLD}{color}│{RESET} {BOLD}Body:{RESET}")
            if isinstance(body, dict) or isinstance(body, list):
                try:
                    formatted_json = json.dumps(body, indent=2)
                    for line in formatted_json.split("\n"):
                        # Limit output length to avoid terminal flood
                        print(f"{BOLD}{color}│{RESET}   {line}")
                except:
                    print(f"{BOLD}{color}│{RESET}   {body}")
            else:
                text = str(body)
                if len(text) > 1000:
                    text = text[:1000] + "... [truncated]"
                for line in text.split("\n"):
                    print(f"{BOLD}{color}│{RESET}   {line}")

        print(f"{BOLD}{color}└{'─' * 61}┘{RESET}\n")

    @staticmethod
    def log_email(to: str, subject: str, success: bool, error: Optional[str] = None):
        """Special logging for Email attempts."""
        color = GREEN if success else RED
        status = "SENT" if success else "FAILED"

        print(f"\n{BOLD}{color}┌─── EMAIL VENTURE: {status} {'─' * (42 - len(status))}──┐{RESET}")
        print(f"{BOLD}{color}│{RESET} {BOLD}To:     {RESET} {to}")
        print(f"{BOLD}{color}│{RESET} {BOLD}Subject:{RESET} {subject}")

        if error:
            print(f"{BOLD}{color}│{RESET} {BOLD}Error:  {RESET} {YELLOW}{error}{RESET}")

        print(f"{BOLD}{color}└{'─' * 61}┘{RESET}")
