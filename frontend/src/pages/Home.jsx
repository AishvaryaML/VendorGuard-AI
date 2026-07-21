import { useRef, useState } from "react";
import {
  FiCpu,
  FiBarChart2,
  FiMap,
  FiGitBranch,
  FiActivity,
} from "react-icons/fi";
import Navbar from "../components/Navbar.jsx";
import Hero from "../components/Hero.jsx";
import VendorForm from "../components/VendorForm.jsx";
import ResultCard from "../components/ResultCard.jsx";
import Footer from "../components/Footer.jsx";

const NEXT_PHASE_ITEMS = [
  { icon: FiCpu, label: "AI-powered Privacy Policy Analysis" },
  { icon: FiBarChart2, label: "Vendor Risk Scoring" },
  { icon: FiMap, label: "Compliance Mapping" },
  { icon: FiGitBranch, label: "Multi-Agent AI Workflow" },
  { icon: FiActivity, label: "Continuous Monitoring" },
];

function Home() {
  const [result, setResult] = useState(null);
  const [vendorUrl, setVendorUrl] = useState("");
  const formSectionRef = useRef(null);

  const scrollToForm = () => {
    formSectionRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const handleResult = (data, url) => {
    setResult(data);
    setVendorUrl(url);
  };

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <Hero onCtaClick={scrollToForm} />

      <main className="mx-auto max-w-3xl px-6 py-16" ref={formSectionRef}>
        <VendorForm onResult={handleResult} />
        <ResultCard result={result} vendorUrl={vendorUrl} />

        <section id="about" className="mt-16 card-surface p-6 md:p-8">
          <span className="eyebrow">Next Phase</span>
          <h2 className="mt-2 text-xl font-bold text-white">
            What's coming after this prototype
          </h2>
          <p className="mt-2 text-sm text-muted">
            This build only discovers and downloads a vendor's privacy
            policy. The features below are planned, not yet implemented.
          </p>

          <ul className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2">
            {NEXT_PHASE_ITEMS.map(({ icon: Icon, label }) => (
              <li
                key={label}
                className="flex items-center gap-3 rounded-lg border border-border bg-background px-4 py-3"
              >
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary/15 text-primary">
                  <Icon size={16} />
                </span>
                <span className="text-sm text-slate-200">{label}</span>
              </li>
            ))}
          </ul>
        </section>
      </main>

      <Footer />
    </div>
  );
}

export default Home;
