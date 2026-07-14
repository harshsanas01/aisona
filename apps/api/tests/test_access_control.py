from carecall_domain import DEFAULT_ROLE, PERMISSIONS_BY_ROLE, ROLES, has_permission


def test_viewer_can_view_but_not_review_or_manage_tasks():
    assert has_permission("viewer", "view") is True
    assert has_permission("viewer", "review") is False
    assert has_permission("viewer", "manage_tasks") is False
    assert has_permission("viewer", "developer_tools") is False


def test_coordinator_can_view_review_and_manage_tasks_but_not_developer_tools():
    assert has_permission("coordinator", "view") is True
    assert has_permission("coordinator", "review") is True
    assert has_permission("coordinator", "manage_tasks") is True
    assert has_permission("coordinator", "developer_tools") is False


def test_admin_has_every_permission():
    for permission in {"view", "review", "manage_tasks", "developer_tools"}:
        assert has_permission("admin", permission) is True


def test_unknown_role_has_no_permissions():
    assert has_permission("not-a-real-role", "view") is False


def test_default_role_is_a_valid_role_with_review_and_manage_tasks():
    """Preserves pre-RBAC behavior: any caller that doesn't send a role
    keeps doing everything it could do before RBAC existed."""
    assert DEFAULT_ROLE in ROLES
    assert has_permission(DEFAULT_ROLE, "review") is True
    assert has_permission(DEFAULT_ROLE, "manage_tasks") is True


def test_every_role_has_view_permission():
    for role in ROLES:
        assert has_permission(role, "view") is True


def test_permissions_by_role_only_contains_known_roles():
    assert set(PERMISSIONS_BY_ROLE.keys()) == set(ROLES)
