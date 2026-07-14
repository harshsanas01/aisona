import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { Header } from '../Header';
import { RoleProvider } from '../../../app/RoleContext';

vi.mock('../../../services/api', () => ({
  getHealth: vi.fn().mockResolvedValue({ status: 'ok', calls_loaded: 21, retrieval_mode: 'hybrid' }),
  ROLE_STORAGE_KEY: 'carecall.role',
}));

function renderHeader() {
  return render(
    <MemoryRouter>
      <RoleProvider>
        <Header onOpenMobileNav={() => {}} />
      </RoleProvider>
    </MemoryRouter>,
  );
}

describe('Header role switcher', () => {
  afterEach(() => {
    localStorage.removeItem('carecall.role');
  });

  it('defaults to Coordinator and persists a new selection to localStorage', async () => {
    const user = userEvent.setup();
    renderHeader();

    const select = await screen.findByLabelText('Acting role');
    expect(select).toHaveValue('coordinator');

    await user.selectOptions(select, 'viewer');
    expect(localStorage.getItem('carecall.role')).toBe('viewer');
  });

  it('restores a previously selected role from localStorage', async () => {
    localStorage.setItem('carecall.role', 'admin');
    renderHeader();

    const select = await screen.findByLabelText('Acting role');
    expect(select).toHaveValue('admin');
  });
});
