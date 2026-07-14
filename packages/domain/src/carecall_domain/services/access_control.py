from typing import Dict, FrozenSet

ROLES = ("viewer", "coordinator", "admin")

# The role assumed when a request carries none - preserves pre-RBAC
# behavior for any caller that doesn't yet send a role (e.g. existing
# tests, scripts, or an internal service call).
DEFAULT_ROLE = "coordinator"

# Permissions:
# - "view": read-only access to timelines, patterns, briefs, tasks, person
#   mentions, and asking questions. Every role has this.
# - "review": confirm/correct/dismiss timeline events, patterns, and person
#   mentions; submit feedback on an answer.
# - "manage_tasks": create/update/complete/reopen coordinator follow-up
#   tasks, and generate briefs.
# - "developer_tools": the audit trail and Retrieval Comparison Lab - this
#   is checked IN ADDITION TO, not instead of, the deployment-level
#   CARECALL_DEVELOPER_MODE flag (see apps/api/src/carecall_api/config.py) -
#   both gates must pass; developer_tools alone does not expose these
#   surfaces on a deployment where developer mode itself is off.
PERMISSIONS_BY_ROLE: Dict[str, FrozenSet[str]] = {
    "viewer": frozenset({"view"}),
    "coordinator": frozenset({"view", "review", "manage_tasks"}),
    "admin": frozenset({"view", "review", "manage_tasks", "developer_tools"}),
}


def has_permission(role: str, permission: str) -> bool:
    return permission in PERMISSIONS_BY_ROLE.get(role, frozenset())
