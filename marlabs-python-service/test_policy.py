from policy_repository import PolicyRepository
from policy_engine import PolicyEngine

repository = PolicyRepository()
engine = PolicyEngine()


# policies = repository.find_eligible_policies(
#     tenant="Atlas", role="employee", as_of="2026-09-21"
# )

# result = engine.evaluate(policies=policies, benefit="home-office")


policies = repository.find_eligible_policies(
    tenant="Boreal", role="employee", as_of="2026-09-21"
)
result = engine.evaluate(policies=policies, benefit="certification")

print(result)
