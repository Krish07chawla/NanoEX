import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { DepthTable } from '../components/trading/DepthTable';
import { StatCard } from '../components/ui';
import { Table } from '../components/ui/Table';
import { Footer, PaperBadge } from '../components/layout/Disclaimer';
import { passwordProblem } from '../pages/Register';

describe('passwordProblem', () => {
  it('rejects short or weak passwords', () => {
    expect(passwordProblem('abc1')).toMatch(/8 characters/);
    expect(passwordProblem('abcdefgh')).toMatch(/letter and one number/);
    expect(passwordProblem('abcdefg1')).toBeNull();
  });
});

describe('ui components', () => {
  it('renders a stat card', () => {
    render(<StatCard label="Equity" value="₹5.00 L" sub="flat" />);
    expect(screen.getByText('Equity')).toBeInTheDocument();
    expect(screen.getByText('₹5.00 L')).toBeInTheDocument();
  });

  it('renders table rows and an empty state', () => {
    const cols = [{ key: 's', header: 'Symbol', render: (r: { s: string }) => r.s }];
    const { rerender } = render(
      <Table columns={cols} rows={[{ s: 'TCS' }, { s: 'INFY' }]} rowKey={(r) => r.s} />,
    );
    expect(screen.getByText('TCS')).toBeInTheDocument();
    expect(screen.getAllByRole('row')).toHaveLength(3);
    rerender(<Table columns={cols} rows={[]} rowKey={(r) => r.s} empty="No trades" />);
    expect(screen.getByText('No trades')).toBeInTheDocument();
  });

  it('shows the paper-trading badge and disclaimer', () => {
    render(
      <>
        <PaperBadge />
        <Footer />
      </>,
    );
    expect(screen.getByText(/PAPER TRADING/)).toBeInTheDocument();
    expect(screen.getByText(/educational simulation/)).toBeInTheDocument();
  });
});

describe('DepthTable', () => {
  it('waits when there is no depth', () => {
    render(<DepthTable depth={null} />);
    expect(screen.getByText(/Waiting for depth/)).toBeInTheDocument();
  });

  it('renders bid and ask levels', () => {
    render(
      <DepthTable
        depth={{
          symbol: 'RELIANCE',
          exchange: 'NSE',
          bids: [{ price: 2500.05, quantity: 120, orders: 3 }],
          asks: [{ price: 2500.4, quantity: 80, orders: 2 }],
        }}
      />,
    );
    expect(screen.getByText('2,500.05')).toBeInTheDocument();
    expect(screen.getByText('2,500.40')).toBeInTheDocument();
  });
});
