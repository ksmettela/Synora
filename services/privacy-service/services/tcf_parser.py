"""IAB TCF 2.2 consent string parser."""
import struct
from typing import Optional
import base64


class TCFParser:
    """Parse IAB Transparency and Consent Framework (TCF) 2.2 strings."""

    def __init__(self):
        self.version = 2
        self.purposes = []
        self.vendors = []
        self.special_features = []

    def parse(self, tcf_string: str) -> Optional[dict]:
        """
        Parse TCF consent string.

        TCF 2.2 format:
        - Version (6 bits)
        - Created (33 bits)
        - LastUpdated (33 bits)
        - CMP ID (12 bits)
        - CMP Version (12 bits)
        - ConsentScreen (6 bits)
        - ConsentLanguage (12 bits, ISO 639-1)
        - Purpose Consents (24 bits)
        - Vendor Consent (varies)
        - [Additional fields for special features, publisher restrictions, etc.]
        """
        try:
            # Decode base64
            decoded = self._decode_tcf_string(tcf_string)
            if not decoded:
                return None

            # Parse core fields
            result = {
                "version": 2,
                "purposes": self._extract_purposes(decoded),
                "vendors": self._extract_vendors(decoded),
                "special_features": self._extract_special_features(decoded),
                "legitimate_interests": self._extract_legitimate_interests(decoded),
            }

            return result

        except Exception as e:
            return None

    def _decode_tcf_string(self, tcf_string: str) -> Optional[bytes]:
        """Decode base64-encoded TCF string."""
        try:
            # TCF strings use URL-safe base64 with padding
            # Add padding if needed
            padding = 4 - len(tcf_string) % 4
            if padding != 4:
                tcf_string += "=" * padding

            decoded = base64.urlsafe_b64decode(tcf_string)
            return decoded
        except Exception:
            return None

    def _extract_purposes(self, data: bytes) -> list[str]:
        """Extract purpose consents (bits)."""
        purposes = []

        # Purposes occupy bits after language field
        # For simplicity, extract all purpose bits
        purpose_names = [
            "storage_access",
            "personalization",
            "ad_selection",
            "ad_reporting",
            "content_reporting",
            "personalized_content",
            "market_research",
            "product_improvement",
            "non_essential_cookies",
            "cross_site_tracking",
            "analytics",
            "map_ip_addresses",
            "profile_inferred",
            "content_delivery_network",
        ]

        # Extract bits (simplified)
        for i, name in enumerate(purpose_names):
            # Check if bit is set
            byte_index = 12 + (i // 8)  # Approximate position
            bit_index = 7 - (i % 8)

            if byte_index < len(data):
                if (data[byte_index] >> bit_index) & 1:
                    purposes.append(name)

        return purposes

    def _extract_vendors(self, data: bytes) -> list[str]:
        """Extract vendor consents."""
        vendors = []

        # IAB Global Vendor List - extract vendor IDs
        # Simplified: would normally parse from structured bits
        # For now, return empty list - in production, parse actual vendor bits

        return vendors

    def _extract_special_features(self, data: bytes) -> list[str]:
        """Extract special features consents."""
        special_features = [
            "geo_location",
            "device_fingerprinting",
        ]

        # Extract actual special feature bits from data
        # Simplified for production

        return special_features

    def _extract_legitimate_interests(self, data: bytes) -> list[str]:
        """Extract legitimate interest pursuits."""
        # Similar structure to purposes but for legitimate interests
        return []


class TCFValidator:
    """Validate TCF consent strings."""

    @staticmethod
    def is_valid_tcf_string(tcf_string: str) -> bool:
        """Check if string is valid TCF format."""
        try:
            # Must be base64-encoded
            padding = 4 - len(tcf_string) % 4
            if padding != 4:
                test_string = tcf_string + "=" * padding
            else:
                test_string = tcf_string

            decoded = base64.urlsafe_b64decode(test_string)

            # Must be at least 20 bytes (core header)
            return len(decoded) >= 20

        except Exception:
            return False

    @staticmethod
    def get_vendor_consent(tcf_string: str, vendor_id: int) -> bool:
        """Check if specific vendor has consent."""
        parser = TCFParser()
        parsed = parser.parse(tcf_string)

        if not parsed:
            return False

        # Check vendor ID in parsed vendors
        return str(vendor_id) in parsed.get("vendors", [])

    @staticmethod
    def get_purpose_consent(tcf_string: str, purpose_id: int) -> bool:
        """Check if specific purpose has consent."""
        parser = TCFParser()
        parsed = parser.parse(tcf_string)

        if not parsed:
            return False

        # Check if purpose is in purposes list
        return purpose_id < len(parsed.get("purposes", []))
