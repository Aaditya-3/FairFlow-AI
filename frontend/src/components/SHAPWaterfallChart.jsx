import {
  Bar,
  BarChart,
  Cell,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) {
    return null;
  }

  const item = payload[0].payload;
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-3 text-sm shadow-lg">
      <p className="font-semibold text-slate-900">{item.feature}</p>
      <p className="mt-1 text-slate-500">Value: {String(item.value)}</p>
      <p className="mt-1 font-medium text-slate-700">SHAP: {Number(item.shap_value).toFixed(4)}</p>
    </div>
  );
}

function SHAPWaterfallChart({ waterfallData = [] }) {
  const data = [...waterfallData]
    .sort((first, second) => Math.abs(second.shap_value) - Math.abs(first.shap_value))
    .map((row) => ({
      ...row,
      feature: row.feature.replaceAll("_", " ")
    }));

  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-amber-dark">SHAP Breakdown</p>
          <h3 className="mt-2 text-xl font-bold text-slate-900">Feature contribution waterfall</h3>
        </div>
      </div>
      <div className="h-[360px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ top: 8, right: 24, left: 12, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis type="number" tick={{ fill: "#475569", fontSize: 12 }} />
            <YAxis
              type="category"
              dataKey="feature"
              width={120}
              tick={{ fill: "#334155", fontSize: 12 }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="shap_value" radius={[0, 10, 10, 0]} isAnimationActive>
              {data.map((entry) => (
                <Cell
                  key={`${entry.feature}-${entry.shap_value}`}
                  fill={entry.shap_value >= 0 ? "#16a34a" : "#dc2626"}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-4 flex flex-wrap gap-3 text-xs font-medium text-slate-600">
        <span className="rounded-full bg-emerald-50 px-3 py-1 text-emerald-700">
          Positive values increase hire likelihood
        </span>
        <span className="rounded-full bg-red-50 px-3 py-1 text-red-700">
          Negative values decrease hire likelihood
        </span>
      </div>
    </div>
  );
}

export default SHAPWaterfallChart;
