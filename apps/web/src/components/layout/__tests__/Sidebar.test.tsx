import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { Sidebar } from '../Sidebar';

vi.mock('../../../services/api', () => ({
  getHealth: vi.fn(),
}));

import { getHealth } from '../../../services/api';

function renderSidebar() {
  return render(
    <MemoryRouter>
      <Sidebar collapsed={false} onToggleCollapsed={() => {}} mobileOpen={false} onCloseMobile={() => {}} />
    </MemoryRouter>,
  );
}

describe('Sidebar', () => {
  it('hides devOnly nav items when developer_mode is not enabled', async () => {
    vi.mocked(getHealth).mockResolvedValue({ status: 'ok', calls_loaded: 21, retrieval_mode: 'hybrid' });

    renderSidebar();

    expect(await screen.findByText('Ask')).toBeInTheDocument();
    expect(screen.queryByText('Retrieval Lab')).not.toBeInTheDocument();
  });

  it('shows devOnly nav items when developer_mode is enabled', async () => {
    vi.mocked(getHealth).mockResolvedValue({
      status: 'ok', calls_loaded: 21, retrieval_mode: 'hybrid', developer_mode: true,
    });

    renderSidebar();

    expect(await screen.findByText('Retrieval Lab')).toBeInTheDocument();
  });
});
