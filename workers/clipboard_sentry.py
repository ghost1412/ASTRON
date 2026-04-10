import os
import re
import time

import structlog
import pyperclip
from sqlmodel import text
from core.pii_validator import PIIValidator

from core.db_manager import DatabaseManager
from core.models import NetworkThreat

logger = structlog.get_logger()

class ClipboardSentry:
    """
    Monitors host clipboard for PII exposure.
    Privacy First: Only masked audit logs are stored.
    """
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.last_clipboard = ""
        self.verify_connection()

    def verify_connection(self):
        """Diagnostic startup check."""
        try:
            with DatabaseManager.get_session(self.tenant_id) as session:
                session.execute(text("SELECT 1"))
            logger.info("db_connection_verified", tenant=self.tenant_id)
        except Exception as e:
            logger.error("db_connection_failed", error=str(e))
            print(f"\n[CRITICAL ERROR] Could not connect to ASTRON Database at {os.getenv('DATABASE_URL')}")
            print("Ensure Docker is running and Postgres port 5432 is exposed.\n")
        
    def monitor_loop(self):
        logger.info("clipboard_sentry_started", tenant=self.tenant_id)
        last_heartbeat = time.time()
        
        while True:
            try:
                # Periodic Heartbeat for diagnostics
                if time.time() - last_heartbeat > 30:
                    logger.info("sentry_heartbeat_alive", tenant=self.tenant_id)
                    last_heartbeat = time.time()

                current_value = pyperclip.paste()

                # ONLY ONCE: Diagnostic Pulse Log (to see if the agent is blind)
                if current_value != self.last_clipboard and current_value.strip():
                    pulse_sig = current_value[:5] + "..." if len(current_value) > 5 else current_value
                    logger.debug("clipboard_pulse_detected", length=len(current_value), preview=pulse_sig)
                    print(f"  [Pulse] Clipboard Change Detected ({len(current_value)} chars)")
                
                # Only analyze if clipboard content changed and is not empty
                if current_value != self.last_clipboard and current_value.strip():
                    self.last_clipboard = current_value
                    self.analyze_content(current_value)
                    
            except Exception as e:
                logger.error("clipboard_access_failed", error=str(e))
                
            time.sleep(2) # Check every 2 seconds to minimize CPU impact

    def analyze_content(self, text: str):
        """DLP Analysis: Uses resilient regex with optional heuristic fallback."""
        strict_mode = os.getenv("ASTRON_STRICT_MODE", "false").lower() == "true"
        
        # 1. Regex Match (The 'Shape' of an Aadhaar/PAN)
        aadhaar_match = re.search(r'\b[2-9]\d{3}\s?\d{4}\s?\d{4}\b', text)
        if aadhaar_match:
            match_text = aadhaar_match.group(0)
            
            # 2. Strict Validation Check
            professional_match = PIIValidator.audit_text(match_text)
            if professional_match:
                pii_type, masked_val = professional_match
                self.log_forensic_alert(pii_type, masked_val)
            elif not strict_mode:
                # 3. Heuristic Fallback (v6.5): Enabled in non-strict mode
                logger.info("heuristic_leak_detected", pattern="AADHAAR_LIKE")
                print(f"  [!] Suspicious Pattern: Aadhaar-like sequence found (Checksum Failed)")
                self.log_forensic_alert("POTENTIAL_AADHAAR", f"XXXX-XXXX-{match_text[-4:]}")
            else:
                logger.debug("PII_validation_failed_strict", pattern="AADHAAR_LIKE")
            return

        # Fallback to standard validator for other items
        pii_match = PIIValidator.audit_text(text)
        if pii_match:
            pii_type, masked_val = pii_match
            self.log_forensic_alert(pii_type, masked_val)




    def log_forensic_alert(self, pii_type: str, masked_val: str):
        """Audit Log: Stores the event in the forensic registry."""
        logger.warning("local_data_exposure_detected", type=pii_type, masked=masked_val)
        
        try:
            with DatabaseManager.get_session(self.tenant_id) as session:
                alert = NetworkThreat(
                    source_ip="LOCAL_HOST",
                    dest_ip="CLIPBOARD",
                    protocol="DLP_AUDIT",
                    port=0,
                    threat_type="LOCAL_LEAK",
                    risk_score=0.9,
                    summary=f"Forensic Audit: {pii_type} found in clipboard. Redacted signature: {masked_val}"
                )
                session.add(alert)
                session.commit()
                session.refresh(alert)
                logger.info("forensic_alert_persisted", id=str(alert.id), type=pii_type)
                print(f"  [✓] Forensic Evidence Logged: {pii_type} (ID: {str(alert.id)[:8]})")
        except Exception as e:
            logger.error("db_persistence_failed", error=str(e))


if __name__ == "__main__":
    tenant = os.getenv("ACTIVE_TENANT", "abcdee")
    sentry = ClipboardSentry(tenant)
    sentry.monitor_loop()
