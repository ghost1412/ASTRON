import math
from typing import Dict, List, Tuple, Optional

class SecurityIntelligence:
    """
    Behavioral Analysis Engine (v6.0)
    Uses statistical and context-aware logic to identify sophisticated threats.
    """
    
    # Local Threat Intel Repository (Representing known C2, Botnets, and Malicious Exit Nodes)
    THREAT_INTEL_DB = {
        "185.156.177.121": "Known Tor Exit Node",
        "103.224.182.251": "Suspected BitRAT C2",
        "45.147.229.177": "Common Brute-Force Actor",
        "1.1.1.1": "Safe: Cloudflare DNS",
        "8.8.8.8": "Safe: Google DNS"
    }

    @staticmethod
    def calculate_entropy(data: bytes) -> float:
        """
        Calculates Shannon Entropy (0.0 to 8.0).
        High entropy (>7.2) usually indicates encrypted or compressed data exfiltration.
        """
        if not data:
            return 0.0
        
        entropy = 0
        freq = {}
        for b in data:
            freq[b] = freq.get(b, 0) + 1
            
        for count in freq.values():
            p = count / len(data)
            entropy -= p * math.log2(p)
            
        return round(entropy, 2)

    @classmethod
    def analyze_risk(cls, dst_ip: str, payload: bytes) -> Tuple[float, str]:
        """
        Combined Behavioral Risk Analysis.
        Returns: Tuple[RiskScore, Summary]
        """
        score = 0.0
        details = []

        # 1. Reputation Check
        if dst_ip in cls.THREAT_INTEL_DB:
            if "Safe" in cls.THREAT_INTEL_DB[dst_ip]:
                return 0.0, "Trusted Destination"
            score += 0.95
            details.append(f"Known Malicious IP: {cls.THREAT_INTEL_DB[dst_ip]}")

        # 2. Entropy Check (Only for large enough payloads to be statistically significant)
        if len(payload) > 64:
            entropy = cls.calculate_entropy(payload)
            if entropy > 7.4: # Very high randomness
                score = max(score, 0.8)
                details.append(f"High-Entropy Payload ({entropy}): Potential Encrypted Exfiltration")
            elif entropy > 6.0 and len(payload) > 1000:
                score = max(score, 0.45)
                details.append(f"Medium-Entropy Large Payload ({entropy})")

        # 3. Protocol Guard (Simplified)
        # If payload starts with non-printable characters but destination is port 80
        if len(payload) > 10 and not all(32 <= b <= 126 or b in [10, 13] for b in payload[:10]):
            score = max(score, 0.5)
            details.append("Anomalous Binary Data over standard protocols")

        summary = " | ".join(details) if details else "Baseline behavior"
        return min(score, 1.0), summary
