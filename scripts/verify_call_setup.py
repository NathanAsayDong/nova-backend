"""
Preflight for outbound report calls, without spending a call.

Checks each link in the chain in the order it actually fails in practice:
Twilio credentials, the from/to numbers against what the account really owns,
the public tunnel, and finally the answer webhook itself — signed exactly the
way Twilio signs it, so a signature-verification mismatch shows up here rather
than as thirty seconds of silence on a real call.

Run with:
    uv run python scripts/verify_call_setup.py
"""

import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv()

from twilio.request_validator import RequestValidator  # noqa: E402
from twilio.rest import Client  # noqa: E402

from src.service.twilio_service import (  # noqa: E402
    CALL_ANSWER_PATH,
    TwilioService,
)

OK = "  ok  "
BAD = " FAIL "


def report(passed: bool, label: str, detail: str = "") -> bool:
    print(f"[{OK if passed else BAD}] {label}")
    if detail:
        for line in detail.splitlines():
            print(f"         {line}")
    return passed


def main() -> int:
    service = TwilioService()
    failures = 0

    print("Nova outbound call preflight\n")

    # 1. Local configuration
    configured, problem = service.is_configured()
    if not report(configured, "configuration present", problem or ""):
        print("\nFix the configuration above before anything else can work.")
        return 1

    from_number = service.from_number
    to_number = service.target_number
    base = service.public_base_url()

    # 2. The numbers, against what the account actually has
    try:
        client = service.client
        owned = [n.phone_number for n in client.incoming_phone_numbers.list(limit=50)]
        verified = [c.phone_number for c in client.outgoing_caller_ids.list(limit=50)]
    except Exception as exc:
        report(False, "Twilio credentials", str(exc))
        return 1
    report(True, "Twilio credentials accepted")

    if not report(
        from_number in owned,
        f"from-number {from_number} is owned by this account",
        "" if from_number in owned else f"Numbers you own: {', '.join(owned) or '(none)'}",
    ):
        failures += 1

    # Trial accounts may only dial verified numbers. On a paid account this is
    # informational, so it is reported but never fails the run.
    if to_number in verified:
        report(True, f"to-number {to_number} is a verified caller id")
    else:
        print(
            f"[ note ] to-number {to_number} is not in this account's verified list.\n"
            f"         Fine on a paid account; on a trial account the call will be\n"
            f"         rejected. Verified: {', '.join(verified) or '(none)'}"
        )

    # 3. The voice. A voice id Twilio doesn't recognise fails at TwiML
    #    execution time, so the call connects and then plays "an application
    #    error has occurred" — nothing before this point catches it.
    voice = service.call_voice_id()
    personal = (os.getenv("ELEVEN_LABS_VOICE_ID") or "").strip()
    if personal and voice == personal:
        failures += 1
        report(
            False,
            "call voice is a ConversationRelay voice",
            f"'{voice}' is your own ElevenLabs account's voice id, which Twilio\n"
            "cannot resolve (error 64112). Set NOVA_CALL_VOICE_ID to a voice from\n"
            "https://www.twilio.com/docs/voice/conversationrelay/voice-configuration",
        )
    else:
        report(True, f"call voice {voice}")

    # 4. The tunnel
    try:
        health = requests.get(f"{base}/health", timeout=10, headers={"User-Agent": "TwilioProxy/1.1"})
        reachable = health.ok
        detail = "" if reachable else f"GET {base}/health returned {health.status_code}"
    except Exception as exc:
        reachable = False
        detail = f"{base} is not reachable: {exc}"
    if not report(reachable, f"backend reachable at {base}", detail):
        failures += 1
        print("\nTwilio must reach this backend. Is the tunnel up and the server running?")
        return 1

    # 5. The answer webhook, signed the way Twilio signs it. This is the step
    #    that catches a PUBLIC_BASE_URL that no longer matches the tunnel: the
    #    signature covers the URL, so a stale value fails here and nowhere else.
    answer_url = f"{service.webhook_url(CALL_ANSWER_PATH)}?update_id=0"
    params = {"CallSid": "CApreflight", "AnsweredBy": "human"}
    signature = RequestValidator(service.auth_token).compute_signature(answer_url, params)

    try:
        response = requests.post(
            answer_url,
            data=params,
            headers={"X-Twilio-Signature": signature, "User-Agent": "TwilioProxy/1.1"},
            timeout=15,
        )
    except Exception as exc:
        report(False, "answer webhook responds", str(exc))
        return 1

    if response.status_code == 403:
        failures += 1
        report(
            False,
            "answer webhook accepts Twilio's signature",
            "Got 403. The running server's PUBLIC_BASE_URL does not match the URL\n"
            "being signed — restart the API process so it picks up the current .env.",
        )
    elif response.status_code == 404:
        # update_id=0 does not exist; reaching the 404 means signature
        # verification passed, which is the thing under test.
        report(True, "answer webhook accepts Twilio's signature")
        report(True, "TwiML handler reached (404 for the dummy update is expected)")
    elif response.ok and "ConversationRelay" in response.text:
        report(True, "answer webhook accepts Twilio's signature")
        report(True, "TwiML returned with a ConversationRelay session")
    else:
        failures += 1
        report(
            False,
            "answer webhook behaved unexpectedly",
            f"HTTP {response.status_code}: {response.text[:300]}",
        )

    print()
    if failures:
        print(f"{failures} check(s) failed — a call placed now would not connect.")
        return 1
    print("All checks passed. A queued call update should ring through.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
