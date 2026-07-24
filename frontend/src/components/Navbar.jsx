import { FiShield, FiGithub } from "react-icons/fi";

const NAV_LINKS = [
  { label: "Home", href: "#home" },
  { label: "Features", href: "#features" },
  { label: "Workflow", href: "#workflow" },
  { label: "Analyze", href: "#prototype" },
];

function Navbar() {
  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background/90 backdrop-blur">
      <nav className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
        {/* Logo */}
        <a href="#home" className="flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/20 text-primary shadow-lg">
            <FiShield size={22} />
          </span>

          <div>
            <h1 className="text-lg font-bold tracking-wide text-white">
              VendorGuard <span className="text-primary">AI</span>
            </h1>
            <p className="text-[11px] text-slate-400">
              Vendor Risk Intelligence
            </p>
          </div>
        </a>

        {/* Navigation */}
        <div className="hidden items-center gap-8 md:flex">
          {NAV_LINKS.map((link) => (
            <a
              key={link.label}
              href={link.href}
              className="text-sm font-medium text-slate-300 transition duration-300 hover:text-primary"
            >
              {link.label}
            </a>
          ))}
        </div>

        {/* GitHub Button */}
        <a
          href="https://github.com/YOUR_GITHUB_USERNAME/VendorGuard-AI"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 rounded-xl border border-primary/40 bg-primary/10 px-4 py-2 text-sm font-semibold text-white transition-all duration-300 hover:bg-primary hover:text-black"
        >
          <FiGithub size={18} />
          <span className="hidden sm:inline">View Project</span>
        </a>
      </nav>
    </header>
  );
}

export default Navbar;