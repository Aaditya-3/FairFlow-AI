import { BriefcaseBusiness, Building2, HeartPulse, SlidersHorizontal } from "lucide-react";

const iconByDomain = {
  hiring: BriefcaseBusiness,
  lending: Building2,
  healthcare: HeartPulse,
  custom: SlidersHorizontal
};

const descriptionByDomain = {
  hiring: "Audit candidate hiring outcomes for fairness and compliance.",
  lending: "Inspect loan approval decisions for protected-group disparities.",
  healthcare: "Review admission decisions across patient demographics.",
  custom: "Map your own schema and run the same fairness pipeline."
};

const customTemplate = {
  domain: "custom",
  display_name: "Custom",
  outcome_column: "outcome",
  outcome_positive_value: 1,
  protected_attributes: ["gender"],
  feature_columns: [],
  outcome_label: "Approved",
  subject_label: "Record",
  required_columns: [],
  column_map: {}
};

function DomainSelector({ templates = [], selectedDomain, onSelect }) {
  const cards = [...templates];
  if (!cards.find((template) => template.domain === "custom")) {
    cards.push(customTemplate);
  }

  return (
    <section className="section-card border border-slate-200 bg-white">
      <p className="text-sm font-semibold uppercase tracking-[0.18em] text-amber-dark">Step 1 of 2</p>
      <h3 className="mt-2 text-2xl font-bold text-slate-900">Choose your domain preset</h3>
      <p className="mt-3 text-sm leading-7 text-slate-600">
        Select a schema template. You can still adjust outcome and protected columns before upload.
      </p>

      <div className="mt-6 grid gap-4 md:grid-cols-2">
        {cards.map((template) => {
          const Icon = iconByDomain[template.domain] || SlidersHorizontal;
          const isSelected = selectedDomain === template.domain;
          return (
            <div
              key={template.domain}
              className={`group rounded-3xl border p-5 transition ${
                isSelected
                  ? "border-amber bg-amber/5 shadow-[0_0_0_1px_rgba(245,158,11,0.35)]"
                  : "border-slate-200 bg-slate-50 hover:border-amber/50 hover:bg-amber/5"
              }`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="rounded-2xl bg-white p-3 text-navy shadow-sm">
                  <Icon className="h-5 w-5" />
                </div>
                <span className="rounded-full bg-slate-100 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">
                  {template.domain}
                </span>
              </div>

              <h4 className="mt-4 text-xl font-bold text-slate-900">{template.display_name}</h4>
              <p className="mt-2 text-sm text-slate-600">{descriptionByDomain[template.domain]}</p>

              <div className="mt-4 rounded-2xl border border-slate-200 bg-white px-4 py-3">
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Required columns</p>
                <p className="mt-2 max-h-14 overflow-hidden text-xs leading-5 text-slate-600 transition-all group-hover:max-h-40">
                  {template.required_columns?.length ? template.required_columns.join(", ") : "Configured manually"}
                </p>
              </div>

              <button
                type="button"
                onClick={() => onSelect?.(template)}
                className={`mt-4 w-full rounded-2xl px-4 py-3 text-sm font-semibold transition ${
                  isSelected
                    ? "bg-navy text-white"
                    : "border border-slate-200 bg-white text-slate-700 hover:border-amber hover:text-amber-dark"
                }`}
              >
                {isSelected ? "Selected" : "Use this domain"}
              </button>
            </div>
          );
        })}
      </div>
    </section>
  );
}

export default DomainSelector;
