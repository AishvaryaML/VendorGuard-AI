import { FiCheckCircle, FiExternalLink, FiFileText } from "react-icons/fi";

function Field({ label, children }) {
  return (
    <div className="border-b border-border py-3 last:border-b-0 sm:flex sm:items-start sm:justify-between sm:gap-6">
      <dt className="text-sm font-medium text-muted">{label}</dt>
      <dd className="mt-1 text-sm text-slate-200 sm:mt-0 sm:text-right">
        {children}
      </dd>
    </div>
  );
}

function ResultCard({ result, vendorUrl }) {
  if (!result) return null;

  return (
    <div className="card-surface mt-8 p-6 md:p-8">
      <div className="flex items-center justify-between gap-4">
        <h3 className="text-lg font-bold text-white">
          Vendor Analysis Summary
        </h3>

        <span className="flex items-center gap-1.5 rounded-full bg-emerald-500/15 px-3 py-1 text-xs font-semibold text-emerald-400">
          <FiCheckCircle size={14} />
          AI Analysis Completed
        </span>
      </div>

      <dl className="mt-5">
        <Field label="Vendor Website">
          {vendorUrl}
        </Field>

        <Field label="Privacy Policy Status">
          <span className="inline-flex items-center gap-1.5 text-emerald-400">
            <FiCheckCircle size={14} />
            {result.message}
          </span>
        </Field>

        <Field label="Privacy Policy URL">
          <a
            href={result.privacy_policy_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-accent hover:underline"
          >
            {result.privacy_policy_url}
            <FiExternalLink size={13} />
          </a>
        </Field>

        <Field label="Document Size">
          {result.characters_downloaded?.toLocaleString()} characters
        </Field>

        <Field label="Status">
          <span className="text-emerald-400">Completed</span>
        </Field>
      </dl>

      {result.analysis && (
        <div className="mt-6">
          <div className="mb-2 flex items-center gap-2 text-sm font-medium text-muted">
            <FiFileText size={15} />
            AI Analysis
          </div>

          <div className="rounded-lg border border-border bg-background p-4">
            <pre className="whitespace-pre-wrap text-sm leading-relaxed text-slate-300">
              {result.analysis}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}

export default ResultCard;