from typing import List, Dict


class PolicyEngine:

    def evaluate(self, policies: List[Dict], benefit: str):

        if not policies:
            return {"status": "INSUFFICIENT_EVIDENCE", "answer": None, "citations": []}

        relevant = self._find_relevant(policies, benefit)

        if not relevant:
            return {"status": "INSUFFICIENT_EVIDENCE", "answer": None, "citations": []}

        # Multiple applicable policies with no
        # supplied precedence rule = conflict.
        if len(relevant) > 1:

            return {
                "status": "CONFLICT",
                "answer": None,
                "citations": [
                    {"chunk_id": policy["id"], "quote": policy["text"]}
                    for policy in relevant
                ],
            }

        policy = relevant[0]

        return {
            "status": "ANSWERED",
            "answer": self._build_answer(policy),
            "citations": [{"chunk_id": policy["id"], "quote": policy["text"]}],
        }

    def _find_relevant(self, policies: List[Dict], benefit: str):

        benefit = benefit.lower()

        results = []

        for policy in policies:

            text = policy["text"].lower()

            if benefit in text:
                results.append(policy)

        return results

    def _build_answer(self, policy):

        return f"According to policy " f"{policy['id']}: " f"{policy['text']}"
