import { useRef, useState } from "react";
import {
  FiGlobe,
  FiSearch,
  FiShield,
  FiBarChart2,
  FiFileText,
} from "react-icons/fi";

import Navbar from "../components/Navbar.jsx";
import Hero from "../components/Hero.jsx";
import VendorForm from "../components/VendorForm.jsx";
import ResultCard from "../components/ResultCard.jsx";
import Footer from "../components/Footer.jsx";

const WORKFLOW = [
  {
    icon: FiGlobe,
    title: "Scraper Agent",
    description: "Collects vendor website and privacy policy.",
  },
  {
    icon: FiSearch,
    title: "Policy Analyzer",
    description: "Extracts privacy and security information.",
  },
  {
    icon: FiShield,
    title: "Risk Engine",
    description: "Calculates AI-powered vendor risk score.",
  },
  {
    icon: FiBarChart2,
    title: "Compliance Checker",
    description: "Maps policies against compliance standards.",
  },
  {
    icon: FiFileText,
    title: "AI Report",
    description: "Generates explainable vendor assessment report.",
  },
];

function Home() {
  const [result, setResult] = useState(null);
  const [vendorUrl, setVendorUrl] = useState("");

  const formSectionRef = useRef(null);

  const scrollToForm = () => {
    formSectionRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  };

  const handleResult = (data, url) => {
    setResult(data);
    setVendorUrl(url);
  };

  return (
    <div className="min-h-screen bg-background">

      <Navbar />

      <Hero onCtaClick={scrollToForm} />

      <main
        className="mx-auto max-w-7xl px-6 py-20"
        ref={formSectionRef}
      >
        <VendorForm
          onResult={handleResult}
        />

        <ResultCard
          result={result}
          vendorUrl={vendorUrl}
        />

        {/* Workflow */}

        <section
          id="workflow"
          className="mt-20 rounded-2xl border border-border bg-slate-900/50 p-8"
        >
          <span className="eyebrow">
            AI WORKFLOW
          </span>

          <h2 className="mt-3 text-3xl font-bold text-white">
            How VendorGuard AI Works
          </h2>

          <p className="mt-3 max-w-3xl text-slate-400">
            VendorGuard AI uses an Agentic AI workflow to analyze third-party
            vendors and generate explainable vendor risk reports.
          </p>

          <div className="mt-10 grid gap-6 md:grid-cols-5">

            {WORKFLOW.map((item) => {
              const Icon = item.icon;

              return (
                <div
                  key={item.title}
                  className="rounded-xl border border-border bg-background p-6 text-center transition hover:border-primary hover:-translate-y-1"
                >
                  <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-primary/10 text-primary">
                    <Icon size={28} />
                  </div>

                  <h3 className="mt-5 text-lg font-semibold text-white">
                    {item.title}
                  </h3>

                  <p className="mt-3 text-sm text-slate-400">
                    {item.description}
                  </p>
                </div>
              );
            })}

          </div>
        </section>

      </main>

      <Footer />

    </div>
  );
}

export default Home;