import os
import time
import structlog
from datetime import datetime
from scapy.all import sniff, IP, TCP, UDP
from core.db_manager import DatabaseManager
from core.models import NetworkThreat
from sqlmodel import Session

logger = structlog.get_logger()

# CONFIGURATION: Professional Security Baselines
SUSPICIOUS_PORTS = {
    4444: "Metasploit Default C2",
    6667: "Legacy IRC Botnet",
    1337: "Common Hacker Backdoor",
    31337: "Back Orifice",
    8008: "Suspicious Proxy Activity"
}

from core.pii_validator import PIIValidator
from core.security_intelligence import SecurityIntelligence

class NeuralSentry:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.packet_count = 0
        self.threat_count = 0
        self.threat_cache = {} # (src, dst, type, summary) -> last_reported_timestamp
        
    def analyze_packet(self, packet):
        """Passive Analysis Loop: Integrated Behavioral & Signature Engine."""
        if not packet.haslayer(IP):
            return

        self.packet_count += 1
        src = packet[IP].src
        dst = packet[IP].dst
        payload = bytes(packet[TCP].payload) if packet.haslayer(TCP) else b""
        proto = "TCP" if packet.haslayer(TCP) else "UDP" if packet.haslayer(UDP) else "OTHER"
        
        # 1. Signature-Based Port Monitoring
        port = 0
        if packet.haslayer(TCP): port = packet[TCP].dport
        elif packet.haslayer(UDP): port = packet[UDP].dport
        
        if port in SUSPICIOUS_PORTS:
            self.report_threat(
                src, dst, proto, port, 
                "MALWARE", 0.9, 
                f"Suspicious port {port} detected: {SUSPICIOUS_PORTS[port]}"
            )

        # 2. Behavioral Sophistication: Entropy & Reputation
        risk_score, risk_summary = SecurityIntelligence.analyze_risk(dst, payload)
        if risk_score > 0.4:
            self.report_threat(
                src, dst, proto, port,
                "BEHAVIORAL", risk_score,
                risk_summary
            )

        # 3. Forensic Deep Packet Inspection (DPI) for PII
        if payload:
            try:
                # Decoded raw bytes to string for regex/stdnum analysis
                payload_str = payload.decode('utf-8', errors='ignore')
                pii_match = PIIValidator.audit_text(payload_str)
                if pii_match:
                    pii_type, masked_val = pii_match
                    self.report_threat(
                        src, dst, proto, port,
                        "DATA_LEAK", 0.85,
                        f"Sensitive {pii_type} detected in outbound stream. Identification: {masked_val}"
                    )
            except Exception:
                pass


    def report_threat(self, src: str, dst: str, proto: str, port: int, t_type: str, score: float, summary: str):
        """Persists detected threat to the sharded database mesh with 60s deduplication."""
        
        # Incident Deduplication: Avoid flooding the registry with identical packets
        cache_key = (src, dst, t_type, summary)
        now = time.time()
        
        if cache_key in self.threat_cache:
            if now - self.threat_cache[cache_key] < 60:
                # Still in cooldown period
                return
        
        self.threat_cache[cache_key] = now
        logger.warning("threat_detected", type=t_type, src=src, score=score)
        self.threat_count += 1

        
        try:
            with DatabaseManager.get_session(self.tenant_id) as session:
                threat = NetworkThreat(
                    source_ip=src,
                    dest_ip=dst,
                    protocol=proto,
                    port=port,
                    threat_type=t_type,
                    risk_score=score,
                    summary=summary
                )
                session.add(threat)
                session.commit()
        except Exception as e:
            logger.error("db_persistence_failed", error=str(e))

    def run(self):
        """Starts the passive sniffing loop on the host interface."""
        logger.info("sentry_started", tenant=self.tenant_id, scope="ENTIRE_HOST")
        # filter="not port 5432 and not port 6379" helps reduce noise from internal ASTRON comms
        # Added port 8000 to suppression list
        sniff(prn=self.analyze_packet, store=0, filter="not port 5432 and not port 6379 and not port 9200 and not port 8000")


if __name__ == "__main__":
    tenant = os.getenv("ACTIVE_TENANT", "system-sentry")
    sentry = NeuralSentry(tenant)
    sentry.run()
