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
            flags.append("The linked local device record is marked as an emulator; this does not independently verify hardware or intent.")

        if shared_accounts_count > 1:
            flags.append(f"Local transaction records link this device fingerprint with {shared_accounts_count - 1} other account profile(s); ownership or authorization was not verified.")

        if shared_identities_count > 1:
            flags.append(f"Local transaction records link this payment identity with {shared_identities_count} account profile(s); credential ownership was not verified.")

        if payment_identity.get("risk_flags"):
            flags.append(f"Payment credential active risk tags: {', '.join(payment_identity.get('risk_flags'))}.")

        account_age = customer.get("account_age_days", 30)
        if account_age < 7:
            flags.append(f"The local customer record lists an account age of {account_age} days; this is a heuristic review signal.")

        # Attempt LLM analysis if configured
        llm_response = None
        if self.has_llm:
            provider_context = {
                "device_type": device.get("device_type", "UNKNOWN"),
                "emulator_flag_in_local_record": bool(is_emulator),
                "shared_device_account_count": shared_accounts_count,
                "shared_payment_identity_account_count": shared_identities_count,
                "payment_identity_risk_flag_count": len(payment_identity.get("risk_flags") or []),
                "account_age_days_in_local_record": account_age,
                "ip_address_present": bool(ip_address),
                "review_signal_count": len(flags),
            }
            prompt = f"Summarize these aggregated, unverified local review signals only: {provider_context}. Do not infer a person's identity, intent, device hardware, or fraud status."
            system = "You are an Identity Intelligence Agent. Use only the supplied aggregate fields and do not invent evidence. Return JSON with keys: summary, flags (list)."
            llm_response = self._call_llm_if_available(prompt, system)

        if llm_response and "summary" in llm_response:
            return {
                "is_llm_generated": True,
                "summary": llm_response.get("summary"),
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
            + (f"Local review signals: {'; '.join(flags)}." if flags else "No identity risk flags were found in the available local records; identity was not independently verified.")
        )

        return {
            "is_llm_generated": False,
            "summary": summary,
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
