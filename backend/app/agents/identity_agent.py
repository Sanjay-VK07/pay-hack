from typing import Dict, Any, List
from app.agents.base_agent import BaseAgent

class IdentityIntelligenceAgent(BaseAgent):
    name: str = "Identity Intelligence Agent"
    stage: str = "IDENTITY_INTEL"
    description: str = "Investigates device fingerprints, emulator runtime, IP indicators, and payment credential sharing."

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        device = inputs.get("device") or {}
        payment_identity = inputs.get("payment_identity") or {}
        customer = inputs.get("customer") or {}
        shared_accounts_count = inputs.get("shared_accounts_count", 0)
        shared_identities_count = inputs.get("shared_identities_count", 0)
        ip_address = inputs.get("ip_address")
        device_fingerprint = device.get("device_fingerprint") or None

        flags: List[str] = []
        is_emulator = device.get("is_emulator", False)
        
        if is_emulator:
            flags.append("Device runtime identified as an emulated virtual environment (anti-fraud bypass signature).")

        if shared_accounts_count > 1:
            flags.append(f"Device fingerprint '{device.get('device_fingerprint', '')[:8]}...' shared with {shared_accounts_count - 1} other unrelated accounts.")

        if shared_identities_count > 1:
            flags.append(f"Payment credential '{payment_identity.get('masked_value', 'Unknown')}' linked across {shared_identities_count} distinct account profiles.")

        if payment_identity.get("risk_flags"):
            flags.append(f"Payment credential active risk tags: {', '.join(payment_identity.get('risk_flags'))}.")

        account_age = customer.get("account_age_days", 30)
        if account_age < 7:
            flags.append(f"Synthetic identity risk: New account created only {account_age} days ago.")

        # Attempt LLM analysis if configured
        llm_response = None
        if self.has_llm:
            prompt = f"Analyze identity for customer {customer.get('email')}, IP {ip_address}, device {device}. Flags: {flags}."
            system = "You are an Identity Intelligence Agent. Return JSON with keys: summary, flags (list), confidence_score (float 0-1)."
            llm_response = self._call_llm_if_available(prompt, system)

        if llm_response and "summary" in llm_response:
            return {
                "is_llm_generated": True,
                "summary": llm_response.get("summary"),
                "confidence_score": llm_response.get("confidence_score", 0.93),
                "findings": {
                    "device_type": device.get("device_type", "UNKNOWN"),
                    "device_fingerprint": device_fingerprint,
                    "is_emulator": is_emulator,
                    "shared_device_accounts": shared_accounts_count,
                    "shared_payment_credentials": shared_identities_count,
                    "ip_address": ip_address,
                    "identity_flags": llm_response.get("flags", flags)
                }
            }

        # Deterministic Expert Output
        summary = (
            f"Device and Identity assessment for {customer.get('full_name', 'User')}. "
            + (f"Observed device fingerprint: {device_fingerprint}. " if device_fingerprint else "")
            + (f"High-threat identity signals detected: {'; '.join(flags)}." if flags else "Valid single-origin hardware profile and payment identity verified.")
        )

        return {
            "is_llm_generated": False,
            "summary": summary,
            "confidence_score": 0.95 if flags else 0.98,
            "findings": {
                "device_type": device.get("device_type", "UNKNOWN"),
                "device_fingerprint": device_fingerprint,
                "is_emulator": is_emulator,
                "shared_device_accounts": shared_accounts_count,
                "shared_payment_credentials": shared_identities_count,
                "ip_address": ip_address,
                "identity_flags": flags
            }
        }
