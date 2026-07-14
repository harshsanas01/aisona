from typing import Callable, Optional

from carecall_domain import DEFAULT_ROLE, has_permission
from fastapi import Depends, Header, HTTPException

# Local-dev/demo identity: this app has no real login flow, so the acting
# role travels as a plain request header rather than a signed session/JWT.
# A caller that sends nothing keeps DEFAULT_ROLE's permissions - the same
# behavior every route had before RBAC existed, so no existing caller
# (tests, scripts, the frontend before it sends this header) is broken by
# this addition. See docs/security/roles-and-privacy.md.
ROLE_HEADER_NAME = "X-CareCall-Role"


def get_current_role(x_carecall_role: Optional[str] = Header(default=None, alias=ROLE_HEADER_NAME)) -> str:
    return x_carecall_role or DEFAULT_ROLE


def require_permission(permission: str) -> Callable[[str], str]:
    """FastAPI dependency factory: raises 403 unless the request's role
    (from ROLE_HEADER_NAME, or DEFAULT_ROLE if absent) has `permission`."""

    def _dependency(role: str = Depends(get_current_role)) -> str:
        if not has_permission(role, permission):
            raise HTTPException(
                status_code=403,
                detail=f"Role '{role}' does not have the '{permission}' permission required for this action.",
            )
        return role

    return _dependency
