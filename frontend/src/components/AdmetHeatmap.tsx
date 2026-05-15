import type { FragmentDetail } from "../types";

type EndpointRow = NonNullable<FragmentDetail["admet_summary"]>[number];
type CleanEndpointRow = NonNullable<FragmentDetail["clean_admet_summary"]>[number];

type Metric = {
  label: string;
  aliases: string[];
  unitHint: string;
  description: string;
  score: (value: number, row?: EndpointRow | CleanEndpointRow) => number | null;
};

const metrics: Metric[] = [
  {
    label: "CL",
    aliases: ["CL", "Clearance", "CLint", "CL_renal"],
    unitHint: "low clearance preferred",
    description: "Lower intrinsic or systemic clearance is generally preferred",
    score: (value, row) => {
      const units = norm(row?.standard_units);
      if (units.includes("mlming") || units.includes("ulmin106cells")) return lowGood(value, 10, 60);
      if (units.includes("mlmin1kg1") || units.includes("mlminkg")) return lowGood(value, 5, 25);
      return lowGood(value, 10, 50);
    }
  },
  {
    label: "Papp",
    aliases: ["Papp", "Caco-2", "PAMPA", "Permeability"],
    unitHint: "permeability preferred",
    description: "Higher permeability is generally preferred",
    score: (value, row) => {
      const units = norm(row?.standard_units);
      if (units.includes("binaryclass")) return highGood(value, 1, 0);
      if (units.includes("logpapp")) return highGood(value, -4.7, -6.0);
      return highGood(value, 10, 2);
    }
  },
  {
    label: "Absorption",
    aliases: ["F", "F%", "BA", "Bioavailability", "Absorption", "Fa"],
    unitHint: "high absorption preferred",
    description: "Higher oral absorption or bioavailability is generally preferred",
    score: (value, row) => {
      const units = norm(row?.standard_units);
      if (units.includes("binaryclass")) return highGood(value, 1, 0);
      return highGood(value, 70, 30);
    }
  },
  {
    label: "Solubility",
    aliases: ["Solubility"],
    unitHint: "solubility preferred",
    description: "Higher aqueous solubility is generally preferred",
    score: (value, row) => {
      const units = norm(row?.standard_units);
      if (units.includes("logmoll")) return highGood(value, -3, -6);
      return highGood(value, 50, 5);
    }
  },
  {
    label: "hERG",
    aliases: ["hERG"],
    unitHint: "low liability preferred",
    description: "Lower hERG liability, or higher hERG safety class, is preferred",
    score: (value, row) => {
      const units = norm(row?.standard_units);
      if (units.includes("safetyclass") || units.includes("binaryclass")) return highGood(value, 1, 0);
      if (units.includes("inhibition") || units.includes("percent") || units === "") return lowGood(value, 10, 50);
      return highGood(value, 10000, 1000);
    }
  },
  {
    label: "LD50",
    aliases: ["LD50"],
    unitHint: "high LD50 preferred",
    description: "Higher LD50 or safety-transformed toxicity value is preferred",
    score: (value, row) => {
      const units = norm(row?.standard_units);
      if (units.includes("log1molkg")) return highGood(value, 3.5, 1.5);
      return highGood(value, 1000, 100);
    }
  },
  {
    label: "DILI",
    aliases: ["DILI"],
    unitHint: "safety class",
    description: "Higher DILI safety class is preferred",
    score: (value) => highGood(value, 1, 0)
  },
  {
    label: "LogD",
    aliases: ["LogD"],
    unitHint: "ideal window",
    description: "A moderate lipophilicity window is usually preferred",
    score: (value) => windowGood(value, 1, 3, -0.5, 5)
  },
  {
    label: "Half-life",
    aliases: ["Half-life", "Half life", "T1/2"],
    unitHint: "hr window",
    description: "A practical half-life window is usually preferred",
    score: (value) => windowGood(value, 2, 12, 0.5, 36)
  }
];

function norm(text: string | null | undefined) {
  return (text ?? "").toLowerCase().replace(/[^a-z0-9]/g, "");
}

function clamp(value: number) {
  return Math.max(0, Math.min(1, value));
}

function highGood(value: number, good: number, bad: number) {
  return clamp((value - bad) / (good - bad));
}

function lowGood(value: number, good: number, bad: number) {
  return clamp((bad - value) / (bad - good));
}

function windowGood(value: number, idealLow: number, idealHigh: number, hardLow: number, hardHigh: number) {
  if (value >= idealLow && value <= idealHigh) return 1;
  if (value < idealLow) return clamp((value - hardLow) / (idealLow - hardLow));
  return clamp((hardHigh - value) / (hardHigh - idealHigh));
}

function colorFor(scoreValue: number | null) {
  if (scoreValue === null) return "bg-slate-100 text-slate-500 border-line";
  if (scoreValue >= 0.75) return "bg-blue-700 text-white border-blue-800";
  if (scoreValue >= 0.5) return "bg-blue-200 text-blue-950 border-blue-300";
  if (scoreValue >= 0.25) return "bg-red-100 text-red-950 border-red-200";
  return "bg-red-600 text-white border-red-700";
}

function bestRow(rows: Array<EndpointRow | CleanEndpointRow>, metric: Metric) {
  const aliases = new Set(metric.aliases.map(norm));
  return rows
    .filter((row) => aliases.has(norm(row.standard_type)) && row.median !== null && row.median !== undefined)
    .sort((a, b) => b.measurement_count - a.measurement_count)[0];
}

function fmt(value: number | null | undefined) {
  if (value === null || value === undefined) return "NA";
  if (Math.abs(value) >= 100) return value.toFixed(0);
  if (Math.abs(value) >= 10) return value.toFixed(1);
  return value.toFixed(2);
}

function rowDescription(row: EndpointRow | CleanEndpointRow | undefined, fallback: string) {
  if (!row) return fallback;
  if ("description" in row && row.description) return row.description;
  return fallback;
}

export default function AdmetHeatmap({
  rows,
  title = "Common ADMET Heatmap",
  subtitle = "Median endpoint values are colored by medicinal chemistry desirability targets. Blue means closer to the preferred range, red means less favorable."
}: {
  rows: Array<EndpointRow | CleanEndpointRow>;
  title?: string;
  subtitle?: string;
}) {
  const cells = metrics.map((metric) => {
    const row = bestRow(rows, metric);
    const median = row?.median ?? null;
    const scoreValue = median === null ? null : metric.score(median, row);
    return { metric, row, median, scoreValue };
  });

  return (
    <section className="rounded-md border border-line bg-white p-5">
      <div className="mb-3 flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <div>
          <h2 className="text-base font-semibold">{title}</h2>
          <p className="mt-1 text-sm text-slate-600">{subtitle}</p>
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-600">
          <span className="h-3 w-6 rounded-sm bg-red-600" />
          Worse
          <span className="h-3 w-6 rounded-sm bg-blue-700" />
          Better
        </div>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        {cells.map(({ metric, row, median, scoreValue }) => (
          <div key={metric.label} className={`min-h-36 rounded-md border p-3 ${colorFor(scoreValue)}`}>
            <div className="text-xs uppercase opacity-80">{metric.label}</div>
            <div className="mt-2 text-2xl font-semibold">{fmt(median)}</div>
            <div className="mt-1 min-h-8 text-xs opacity-90">{row?.standard_units || metric.unitHint}</div>
            <div className="mt-3 text-xs opacity-90">{row ? `${row.standard_type}, n=${row.measurement_count}` : "No matching endpoint"}</div>
            <div className="mt-2 text-xs opacity-80">{rowDescription(row, metric.description)}</div>
          </div>
        ))}
      </div>
    </section>
  );
}
