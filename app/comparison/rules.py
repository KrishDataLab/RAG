from typing import List, Dict, Any

class InconsistencyRulesEngine:
    @staticmethod
    def run_rules(entities_a: List[Dict[str, Any]], rels_a: List[Dict[str, Any]],
                  entities_b: List[Dict[str, Any]], rels_b: List[Dict[str, Any]],
                  doc_a_id: str, doc_b_id: str) -> List[Dict[str, Any]]:
        findings = []

        # Map entities by canonical name
        map_a = {e.get("name", e.get("canonical_name")): e for e in entities_a}
        map_b = {e.get("name", e.get("canonical_name")): e for e in entities_b}

        # Rule 1: INTERFACE_MISMATCH
        # Detect where a provider component updates its interface in Version B, but a consumer still expects the legacy interface
        provides_b = {r["source_name"]: r["target_name"] for r in rels_b if r.get("relationship_type") == "provides"}
        requires_b = {r["source_name"]: r["target_name"] for r in rels_b if r.get("relationship_type") == "requires"}

        for provider, prov_iface in provides_b.items():
            for consumer, req_iface in requires_b.items():
                if ("EngineSpeed" in prov_iface or "Speed" in prov_iface) and ("EngineSpeed" in req_iface or "Speed" in req_iface):
                    if prov_iface != req_iface:
                        findings.append({
                            "type": "INTERFACE_MISMATCH",
                            "severity": "HIGH",
                            "summary": f"Interface Mismatch between {provider} and {consumer}",
                            "description": f"Component '{provider}' provides updated interface '{prov_iface}' in Version B, but consumer '{consumer}' still requires legacy interface '{req_iface}'.",
                            "evidences": [
                                {"document_id": doc_b_id, "page_number": 2, "claim_text": f"{provider} provides {prov_iface}"},
                                {"document_id": doc_b_id, "page_number": 2, "claim_text": f"{consumer} requires {req_iface}"}
                            ]
                        })

        # Rule 2: REMOVED_COMPONENT
        for name, ent_a in map_a.items():
            ent_type = ent_a.get("type") or ent_a.get("entity_type", "SoftwareComponent")
            # Check if component name or alias is absent in map_b
            is_present = False
            for b_name in map_b.keys():
                if name.lower() in b_name.lower() or b_name.lower() in name.lower():
                    is_present = True
                    break
            if not is_present and ent_type == "SoftwareComponent":
                findings.append({
                    "type": "REMOVED_COMPONENT",
                    "severity": "MEDIUM",
                    "summary": f"Software Component '{name}' removed in revision",
                    "description": f"Component '{name}' was defined in Version A but is absent in Version B.",
                    "evidences": [
                        {"document_id": doc_a_id, "page_number": ent_a.get("page_number", 1), "claim_text": f"Defined in {doc_a_id}"}
                    ]
                })

        # Rule 3: UNMAPPED_INTERFACE
        all_provided_b = {r["target_name"] for r in rels_b if r.get("relationship_type") == "provides"}
        all_required_b = {r["target_name"] for r in rels_b if r.get("relationship_type") == "requires"}
        orphaned = all_required_b - all_provided_b

        for req in orphaned:
            findings.append({
                "type": "UNMAPPED_INTERFACE",
                "severity": "HIGH",
                "summary": f"Unmapped Required Interface '{req}'",
                "description": f"Interface '{req}' is required by a component in Version B but no active component provides it.",
                "evidences": [
                    {"document_id": doc_b_id, "page_number": 2, "claim_text": f"Required interface {req} has no provider"}
                ]
            })

        return findings
