import { useState } from "react";
import { FiSearch, FiAlertTriangle } from "react-icons/fi";
import LoadingSpinner from "./LoadingSpinner.jsx";
import { analyzeVendor } from "../services/api.js";

function VendorForm({ onResult }) {
  const [url, setUrl] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!url.trim()) return;

    const trimmedUrl = url.trim();

    setIsLoading(true);
    setError(null);
    onResult(null, trimmedUrl);

    try {
      const data = await analyzeVendor(trimmedUrl);
      onResult(data, trimmedUrl);
    } catch (err) {
      setError("Unable to analyze vendor. Please check the URL.");
      onResult(null, trimmedUrl);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div id="prototype" className="card-surface p-6 md:p-8">
      <h2 className="text-xl font-bold text-white">Vendor Analysis</h2>
      <p className="mt-1 text-sm text-muted">
        Enter a vendor's website to locate and download their privacy policy.
      </p>

      <form onSubmit={handleSubmit} className="mt-6">
        <label
          htmlFor="vendor-url"
          className="mb-2 block text-sm font-medium text-slate-300"
        >
          Vendor Website URL
        </label>

        <div className="flex flex-col gap-3 sm:flex-row">
          <div className="relative flex-1">
            <FiSearch
              className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-muted"
              size={16}
            />
            <input
              id="vendor-url"
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://openai.com"
              disabled={isLoading}
              className="w-full rounded-lg border border-border bg-background py-3 pl-11 pr-4 text-sm text-white placeholder:text-slate-500 focus:border-primary disabled:opacity-60"
            />
          </div>

          <button type="submit" disabled={isLoading} className="btn-primary sm:w-56">
            {isLoading ? (
              <LoadingSpinner label="Analyzing Vendor..." />
            ) : (
              "Analyze Vendor"
            )}
          </button>
        </div>
      </form>

      {error && (
        <div className="mt-5 flex items-start gap-3 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3">
          <FiAlertTriangle className="mt-0.5 shrink-0 text-red-400" size={18} />
          <p className="text-sm text-red-300">{error}</p>
        </div>
      )}
    </div>
  );
}

export default VendorForm;
