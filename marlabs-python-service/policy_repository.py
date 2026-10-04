import json
from datetime import date
from pathlib import Path


class PolicyRepository:

    def __init__(self, file_path: str = "policies.json"):
        self.file_path = Path(file_path)
        self.policies = self._load_policies()

    def _load_policies(self):
        with self.file_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def find_eligible_policies(self, tenant: str, role: str, as_of: str):
        requested_date = date.fromisoformat(as_of)

        eligible = []

        for policy in self.policies:

            # Tenant isolation
            if policy["tenant"] != tenant:
                continue

            # Role isolation
            if policy["role"] != role:
                continue

            # Only approved policies
            if policy["approval_state"] != "Approved":
                continue

            effective_from = date.fromisoformat(policy["effective_from"])

            effective_to = date.fromisoformat(policy["effective_to"])

            # Effective interval:
            # [effective_from, effective_to)
            if not (effective_from <= requested_date < effective_to):
                continue

            eligible.append(policy)

        return eligible
