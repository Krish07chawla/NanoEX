import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

// A plain function stub: the backend reply for the next post() call.
const calls: unknown[][] = [];
let reply: () => unknown = () => ({});
vi.mock('../services/api', async (orig) => {
  const actual = await orig<typeof import('../services/api')>();
  return {
    ...actual,
    post: async (...args: unknown[]) => {
      calls.push(args);
      return reply();
    },
  };
});

import Login from '../pages/Login';
import { ApiError } from '../services/api';
import { useAuthStore } from '../store/authStore';

const renderLogin = () =>
  render(
    <MemoryRouter>
      <Login />
    </MemoryRouter>,
  );

const fill = (container: HTMLElement) => {
  fireEvent.change(container.querySelector('input[type=email]')!, { target: { value: 'a@b.com' } });
  fireEvent.change(container.querySelector('input[type=password]')!, { target: { value: 'secret123' } });
};

describe('Login page', () => {
  beforeEach(() => {
    calls.length = 0;
  });

  it('shows the educational disclaimer', () => {
    renderLogin();
    expect(screen.getByRole('note')).toHaveTextContent(/paper trading/i);
  });

  it('stores the session on success', async () => {
    reply = () => ({
      access_token: 'tok',
      user: { id: '1', email: 'a@b.com', full_name: 'A', role: 'USER' },
    });
    const { container } = renderLogin();
    fill(container);
    fireEvent.click(screen.getByRole('button', { name: /log in/i }));
    await waitFor(() => expect(useAuthStore.getState().accessToken).toBe('tok'));
    expect(calls[0]).toEqual(['/auth/login', { email: 'a@b.com', password: 'secret123' }]);
  });

  it('shows the API error message on failure', async () => {
    reply = () => {
      throw new ApiError('Invalid email or password', 'UNAUTHORIZED', 401);
    };
    const { container } = renderLogin();
    fill(container);
    fireEvent.click(screen.getByRole('button', { name: /log in/i }));
    expect(await screen.findByText('Invalid email or password')).toBeInTheDocument();
  });
});
