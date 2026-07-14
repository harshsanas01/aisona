import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';
import { ROLE_STORAGE_KEY } from '../services/api';

export type Role = 'viewer' | 'coordinator' | 'admin';

export const ROLES: Role[] = ['viewer', 'coordinator', 'admin'];
export const DEFAULT_ROLE: Role = 'coordinator';

const ROLE_LABEL: Record<Role, string> = {
  viewer: 'Viewer (read-only)',
  coordinator: 'Coordinator',
  admin: 'Admin',
};

export function roleLabel(role: Role): string {
  return ROLE_LABEL[role];
}

// "review" mirrors the permission name in the backend's
// carecall_domain.services.access_control module - keep both in sync.
const PERMISSIONS_BY_ROLE: Record<Role, ReadonlySet<string>> = {
  viewer: new Set(['view']),
  coordinator: new Set(['view', 'review', 'manage_tasks']),
  admin: new Set(['view', 'review', 'manage_tasks', 'developer_tools']),
};

export function roleHasPermission(role: Role, permission: string): boolean {
  return PERMISSIONS_BY_ROLE[role].has(permission);
}

interface RoleContextValue {
  role: Role;
  setRole: (role: Role) => void;
  hasPermission: (permission: string) => boolean;
}

const RoleContext = createContext<RoleContextValue | null>(null);

function _readStoredRole(): Role {
  const stored = localStorage.getItem(ROLE_STORAGE_KEY);
  return (ROLES as string[]).includes(stored ?? '') ? (stored as Role) : DEFAULT_ROLE;
}

export function RoleProvider({ children }: { children: ReactNode }) {
  const [role, setRoleState] = useState<Role>(_readStoredRole);

  const setRole = useCallback((next: Role) => {
    localStorage.setItem(ROLE_STORAGE_KEY, next);
    setRoleState(next);
  }, []);

  const hasPermission = useCallback((permission: string) => roleHasPermission(role, permission), [role]);

  const value = useMemo(() => ({ role, setRole, hasPermission }), [role, setRole, hasPermission]);

  return <RoleContext.Provider value={value}>{children}</RoleContext.Provider>;
}

export function useRole() {
  const ctx = useContext(RoleContext);
  if (!ctx) throw new Error('useRole must be used within a RoleProvider');
  return ctx;
}
