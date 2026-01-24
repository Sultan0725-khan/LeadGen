from typing import List, Dict, Tuple
from difflib import SequenceMatcher


class Normalizer:
    """Tool to normalize and deduplicate leads from multiple sources."""

    SIMILARITY_THRESHOLD = 0.85  # 85% similarity for deduplication

    def normalize_and_dedupe(self, raw_leads: List[Dict]) -> List[Dict]:
        """
        Normalize schema and deduplicate leads.

        Returns list of deduplicated leads with merged data from multiple sources.
        """
        if not raw_leads:
            return []

        # Group similar leads
        groups = self._group_similar_leads(raw_leads)

        # Merge each group
        normalized_leads = []
        for group in groups:
            merged = self._merge_leads(group)
            normalized_leads.append(merged)

        print(f"Normalized {len(raw_leads)} leads into {len(normalized_leads)} unique businesses")
        return normalized_leads

    def _group_similar_leads(self, leads: List[Dict]) -> List[List[Dict]]:
        """Group similar leads together for deduplication."""
        groups = []
        used = set()

        for i, lead1 in enumerate(leads):
            if i in used:
                continue

            group = [lead1]
            used.add(i)

            # Find similar leads
            for j, lead2 in enumerate(leads):
                if j <= i or j in used:
                    continue

                if self._are_similar(lead1, lead2):
                    group.append(lead2)
                    used.add(j)

            groups.append(group)

        return groups

    def _are_similar(self, lead1: Dict, lead2: Dict) -> bool:
        """Check if two leads represent the same business."""
        # Compare business names
        name1 = lead1.get("business_name", "").lower()
        name2 = lead2.get("business_name", "").lower()

        if not name1 or not name2:
            return False

        name_similarity = SequenceMatcher(None, name1, name2).ratio()

        # If names are very similar, consider them the same
        if name_similarity >= self.SIMILARITY_THRESHOLD:
            return True

        # If names are somewhat similar, check address or coordinates
        if name_similarity >= 0.7:
            # Check address similarity
            addr1 = lead1.get("address", "").lower()
            addr2 = lead2.get("address", "").lower()

            if addr1 and addr2:
                addr_similarity = SequenceMatcher(None, addr1, addr2).ratio()
                if addr_similarity >= 0.7:
                    return True

            # Check coordinate proximity (within ~100m)
            lat1, lon1 = lead1.get("latitude"), lead1.get("longitude")
            lat2, lon2 = lead2.get("latitude"), lead2.get("longitude")

            if all([lat1, lon1, lat2, lon2]):
                distance = self._haversine_distance(lat1, lon1, lat2, lon2)
                if distance < 0.1:  # < 100 meters
                    return True

        return False

    def _haversine_distance(self, lat1, lon1, lat2, lon2) -> float:
        """Calculate distance in kilometers between two coordinates."""
        from math import radians, sin, cos, sqrt, atan2

        R = 6371  # Earth radius in km

        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))

        return R * c

    def _merge_leads(self, group: List[Dict]) -> Dict:
        """Merge multiple leads into one, tracking data provenance."""
        if len(group) == 1:
            lead = group[0].copy()
            lead["sources"] = [lead.pop("source")]
            return lead

        # Start with first lead as base
        merged = group[0].copy()
        sources = [merged.pop("source")]

        # Track which field came from which source
        field_provenance = {}

        # Merge data from other leads
        for lead in group[1:]:
            source = lead.get("source")
            sources.append(source)

            # Merge each field, preferring non-null values
            for key, value in lead.items():
                if key == "source":
                    continue

                if value and not merged.get(key):
                    merged[key] = value
                    field_provenance[key] = source
                elif value and merged.get(key):
                    # Both have values, keep first but track alternative
                    if key not in field_provenance:
                        field_provenance[key] = sources[0]

        merged["sources"] = list(set(sources))
        merged["field_provenance"] = field_provenance

        return merged
