import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

function histogram(values: number[], bins = 12) {
  if (!values.length) return [];
  const min = Math.min(...values);
  const max = Math.max(...values);
  const width = max === min ? 1 : (max - min) / bins;
  return Array.from({ length: bins }, (_, i) => {
    const lo = min + i * width;
    const hi = lo + width;
    const count = values.filter((value) => (i === bins - 1 ? value >= lo && value <= hi : value >= lo && value < hi)).length;
    return { bin: `${lo.toFixed(1)}`, count };
  });
}

export default function PropertyDistribution({ name, values }: { name: string; values: number[] }) {
  const data = histogram(values);
  return (
    <div className="rounded-md border border-line bg-white p-3">
      <div className="mb-2 text-sm font-semibold uppercase text-slate-600">{name}</div>
      <div className="h-44">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="bin" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
            <Tooltip />
            <Bar dataKey="count" fill="#0f766e" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
