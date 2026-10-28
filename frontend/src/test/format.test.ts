import { describe, expect, it } from 'vitest';
import { formatINR, formatLakh, formatPct, parseTime, pnlClass, signed } from '../utils/format';

describe('format helpers', () => {
  it('formats rupees with Indian grouping', () => {
    expect(formatINR(500000)).toContain('5,00,000');
    expect(formatINR(null)).toBe('—');
  });

  it('formats lakh and crore compactly', () => {
    expect(formatLakh(500000)).toBe('₹5.00 L');
    expect(formatLakh(12000000)).toBe('₹1.20 Cr');
    expect(formatLakh(-250000)).toBe('₹-2.50 L');
  });

  it('adds a sign to positive percentages', () => {
    expect(formatPct(1.234)).toBe('+1.23%');
    expect(formatPct(-0.5)).toBe('-0.50%');
  });

  it('signs positive amounts', () => {
    expect(signed(10, (n) => n.toFixed(0))).toBe('+10');
    expect(signed(-10, (n) => n.toFixed(0))).toBe('-10');
  });

  it('treats timezone-less timestamps as UTC', () => {
    expect(parseTime('2026-01-01T00:00:00').toISOString()).toBe('2026-01-01T00:00:00.000Z');
    expect(parseTime('2026-01-01T05:30:00+05:30').toISOString()).toBe('2026-01-01T00:00:00.000Z');
  });

  it('colours P&L by sign', () => {
    expect(pnlClass(5)).toBe('text-buy');
    expect(pnlClass(-5)).toBe('text-sell');
    expect(pnlClass(0)).toBe('text-fg-muted');
  });
});
