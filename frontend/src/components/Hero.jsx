import { FiArrowDown } from "react-icons/fi";

function Hero({ onCtaClick }) {
  return (
    <section id="home" className="border-b border-border">
      <div className="mx-auto max-w-6xl px-6 py-20 text-center md:py-28">
        <span className="eyebrow">Third-Party Risk Intelligence</span>

        <h1 className="mx-auto mt-4 max-w-3xl text-4xl font-extrabold leading-tight tracking-tight text-white md:text-5xl">
          AI-Powered Third-Party Vendor Risk Intelligence Platform
        </h1>

        <p className="mx-auto mt-6 max-w-2xl text-base text-muted md:text-lg">
          Automatically discover vendor Privacy Policies and prepare them for
          AI-powered risk assessment.
        </p>

        <div className="mt-10">
          <button onClick={onCtaClick} className="btn-primary">
            Analyze Vendor
            <FiArrowDown size={16} />
          </button>
        </div>
      </div>
    </section>
  );
}

export default Hero;
