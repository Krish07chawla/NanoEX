// Recharts wrappers styled for the dark terminal theme.
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { formatAxisINR, formatINR, formatNum } from '../../utils/format';

const AXIS = { stroke: '#3b4857', fontSize: 11, tickLine: false };
const GRID = '#1c2531';
const TOOLTIP = {
  contentStyle: { background: '#131a23', border: '1px solid #2a3542', borderRadius: 6, fontSize: 12 },
  labelStyle: { color: '#8696a7' },
};

export function PriceLine({
  data,
  color = '#f5b942',
  height = 260,
}: {
  data: { label: string; price: number }[];
  color?: string;
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="priceFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.25} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis dataKey="label" {...AXIS} minTickGap={40} />
        <YAxis {...AXIS} domain={['auto', 'auto']} width={70} tickFormatter={(v) => formatNum(v)} />
        <Tooltip {...TOOLTIP} formatter={(v: number) => formatNum(v)} />
        <Area
          type="monotone"
          dataKey="price"
          stroke={color}
          strokeWidth={1.6}
          fill="url(#priceFill)"
          isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function TwoLine({
  data,
  a,
  b,
  labels,
  height = 260,
  money = true,
}: {
  data: Record<string, number | string>[];
  a: string;
  b: string;
  labels: [string, string];
  height?: number;
  money?: boolean;
}) {
  const fmt = (v: number) => (money ? formatAxisINR(v) : formatNum(v));
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis dataKey="x" {...AXIS} minTickGap={40} />
        <YAxis {...AXIS} domain={['auto', 'auto']} width={78} tickFormatter={fmt} />
        <Tooltip {...TOOLTIP} formatter={(v: number) => (money ? formatINR(v) : formatNum(v))} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Line
          type="monotone"
          dataKey={a}
          name={labels[0]}
          stroke="#f5b942"
          dot={false}
          strokeWidth={1.8}
          isAnimationActive={false}
        />
        <Line
          type="monotone"
          dataKey={b}
          name={labels[1]}
          stroke="#4ea8ff"
          dot={false}
          strokeWidth={1.4}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function SingleLine({
  data,
  dataKey,
  height = 240,
  zeroLine,
}: {
  data: Record<string, number | string>[];
  dataKey: string;
  height?: number;
  zeroLine?: boolean;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis dataKey="x" {...AXIS} minTickGap={40} />
        <YAxis {...AXIS} domain={['auto', 'auto']} width={78} tickFormatter={formatAxisINR} />
        <Tooltip {...TOOLTIP} formatter={(v: number) => formatINR(v)} />
        {zeroLine && <ReferenceLine y={0} stroke="#3b4857" />}
        <Line
          type="stepAfter"
          dataKey={dataKey}
          stroke="#f5b942"
          dot={false}
          strokeWidth={1.8}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function PnlBars({
  data,
  labelKey,
  height = 220,
}: {
  data: { pnl: number; [k: string]: string | number }[];
  labelKey: string;
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis dataKey={labelKey} {...AXIS} interval={0} fontSize={10} />
        <YAxis {...AXIS} width={70} tickFormatter={formatAxisINR} />
        <Tooltip {...TOOLTIP} formatter={(v: number) => formatINR(v)} cursor={{ fill: '#1c2531' }} />
        <ReferenceLine y={0} stroke="#3b4857" />
        <Bar dataKey="pnl" name="Net P&L" radius={[3, 3, 0, 0]}>
          {data.map((d, i) => (
            <Cell key={i} fill={d.pnl >= 0 ? '#22c55e' : '#f0525a'} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
