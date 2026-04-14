import { Building2, Sparkles } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { persistSession, register } from "../api/fairlensApi";
import Spinner from "../components/Spinner";

function RegisterPage() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    email: "",
    password: "",
    organization: ""
  });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    try {
      const response = await register(formData);
      persistSession(response);
      navigate("/dashboard", { replace: true });
    } catch (error) {
      return;
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="soft-grid flex min-h-screen items-center justify-center px-4 py-10">
      <div className="glass-panel w-full max-w-3xl overflow-hidden">
        <div className="grid gap-10 bg-white px-8 py-10 sm:px-12 lg:grid-cols-[0.95fr_1.05fr]">
          <div className="rounded-[28px] bg-[linear-gradient(135deg,#0f172a_0%,#1e293b_100%)] p-8 text-white shadow-glow">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/10 px-4 py-2 text-sm font-medium">
              <Sparkles className="h-4 w-4 text-amber-light" />
              Team onboarding
            </div>
            <h1 className="mt-6 text-3xl font-extrabold">Stand up a fairness program in minutes.</h1>
            <p className="mt-4 text-sm leading-7 text-slate-300">
              Register your organization, run your first audit, and create a shared source of
              truth for hiring fairness signals and mitigations.
            </p>
            <div className="mt-8 space-y-4 text-sm text-slate-200">
              <div className="rounded-2xl bg-white/5 p-4">Centralized audit history for every dataset</div>
              <div className="rounded-2xl bg-white/5 p-4">Candidate-level SHAP and counterfactual review</div>
              <div className="rounded-2xl bg-white/5 p-4">Downloadable bias audit PDFs for stakeholders</div>
            </div>
          </div>

          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.24em] text-amber-dark">Get Started</p>
            <h2 className="mt-4 text-3xl font-bold text-slate-900">Create your workspace</h2>
            <p className="mt-3 text-sm leading-6 text-slate-500">
              Use your company email so your reports and mitigation history stay tied to the right
              organization.
            </p>

            <form className="mt-8 space-y-5" onSubmit={handleSubmit}>
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">Organization</label>
                <div className="relative">
                  <Building2 className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" />
                  <input
                    type="text"
                    required
                    value={formData.organization}
                    onChange={(event) => setFormData((current) => ({ ...current, organization: event.target.value }))}
                    className="w-full rounded-2xl border-slate-200 bg-slate-50 px-12 py-3 focus:border-amber focus:ring-amber"
                    placeholder="Northstar Talent"
                  />
                </div>
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">Work Email</label>
                <input
                  type="email"
                  required
                  value={formData.email}
                  onChange={(event) => setFormData((current) => ({ ...current, email: event.target.value }))}
                  className="w-full rounded-2xl border-slate-200 bg-slate-50 px-4 py-3 focus:border-amber focus:ring-amber"
                  placeholder="you@northstar.com"
                />
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">Password</label>
                <input
                  type="password"
                  required
                  minLength={8}
                  value={formData.password}
                  onChange={(event) => setFormData((current) => ({ ...current, password: event.target.value }))}
                  className="w-full rounded-2xl border-slate-200 bg-slate-50 px-4 py-3 focus:border-amber focus:ring-amber"
                  placeholder="At least 8 characters"
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-amber px-4 py-3 text-sm font-semibold text-navy transition hover:bg-amber-light disabled:cursor-not-allowed disabled:opacity-70"
              >
                {loading ? <Spinner /> : <Sparkles className="h-4 w-4" />}
                {loading ? "Creating account..." : "Create Account"}
              </button>
            </form>

            <p className="mt-6 text-sm text-slate-500">
              Already have an account?{" "}
              <Link to="/login" className="font-semibold text-amber-dark transition hover:text-amber">
                Sign in
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default RegisterPage;
