import { FiArrowDown, FiShield, FiActivity, FiFileText, FiLock } from "react-icons/fi";

function Hero({ onCtaClick }) {
  return (
    <section
      id="home"
      className="relative overflow-hidden border-b border-border"
    >
      {/* Background Blur */}
      <div className="absolute left-1/2 top-0 h-96 w-96 -translate-x-1/2 rounded-full bg-primary/10 blur-3xl"></div>

      <div className="relative mx-auto flex max-w-7xl flex-col items-center px-6 py-20 text-center md:py-28">

        {/* Badge */}
        <span className="rounded-full border border-primary/30 bg-primary/10 px-4 py-2 text-sm font-medium text-primary">
          AI Powered • Third-Party Vendor Risk Intelligence
        </span>

        {/* Heading */}
        <h1 className="mt-8 max-w-4xl text-4xl font-extrabold leading-tight tracking-tight text-white md:text-6xl">
          Secure Your Business From
          <span className="text-primary"> Third-Party Vendor Risks</span>
        </h1>

        {/* Description */}
        <p className="mt-6 max-w-3xl text-lg leading-8 text-slate-300">
          VendorGuard AI continuously analyzes vendor websites, privacy
          policies, security practices, and compliance information to generate
          explainable AI-powered vendor risk reports before you trust a third
          party.
        </p>

        {/* Buttons */}
        <div className="mt-10 flex flex-col gap-4 sm:flex-row">
          <button
            onClick={onCtaClick}
            className="btn-primary flex items-center gap-2"
          >
            Analyze Vendor
            <FiArrowDown size={18} />
          </button>

          <a
            href="#workflow"
            className="rounded-xl border border-border px-6 py-3 font-medium text-white transition hover:border-primary hover:text-primary"
          >
            Learn More
          </a>
        </div>

        {/* Stats */}
        <div className="mt-16 grid w-full max-w-5xl grid-cols-2 gap-5 md:grid-cols-4">

          <div className="rounded-2xl border border-border bg-card p-6">
            <FiShield className="mx-auto text-primary" size={28} />
            <h3 className="mt-4 text-lg font-bold text-white">
              Privacy Analysis
            </h3>
            <p className="mt-2 text-sm text-slate-400">
              Detects privacy policy changes and legal risks.
            </p>
          </div>

          <div className="rounded-2xl border border-border bg-card p-6">
            <FiLock className="mx-auto text-primary" size={28} />
            <h3 className="mt-4 text-lg font-bold text-white">
              Security Check
            </h3>
            <p className="mt-2 text-sm text-slate-400">
              Identifies security and trust center information.
            </p>
          </div>

          <div className="rounded-2xl border border-border bg-card p-6">
            <FiActivity className="mx-auto text-primary" size={28} />
            <h3 className="mt-4 text-lg font-bold text-white">
              AI Risk Score
            </h3>
            <p className="mt-2 text-sm text-slate-400">
              Generates explainable vendor risk scores.
            </p>
          </div>

          <div className="rounded-2xl border border-border bg-card p-6">
            <FiFileText className="mx-auto text-primary" size={28} />
            <h3 className="mt-4 text-lg font-bold text-white">
              Smart Reports
            </h3>
            <p className="mt-2 text-sm text-slate-400">
              Creates professional vendor assessment reports.
            </p>
          </div>

        </div>
      </div>
    </section>
  );
}

export default Hero;