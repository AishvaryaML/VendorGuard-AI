import { FiShield, FiGithub } from "react-icons/fi";

const NAV_LINKS = [
  { label: "Home", href: "#home" },
  { label: "About", href: "#about" },
  { label: "Prototype", href: "#prototype" },
];

function Navbar() {
  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background/90 backdrop-blur">
      <nav className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <a href="#home" className="flex items-center gap-2">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/15 text-primary">
            <FiShield size={20} />
          </span>
          <span className="text-lg font-bold tracking-tight text-white">
            VendorGuard <span className="text-accent">AI</span>
          </span>
        </a>

        <div className="hidden items-center gap-8 md:flex">
          {NAV_LINKS.map((link) => (
            <a
              key={link.label}
              href={link.href}
              className="text-sm font-medium text-muted transition-colors hover:text-white"
            >
              {link.label}
            </a>
          ))}
        </div>

        <a
          href="https://github.com"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm font-medium text-slate-200 transition-colors hover:border-primary hover:text-white"
        >
          <FiGithub size={16} />
          <span className="hidden sm:inline">GitHub</span>
        </a>
      </nav>
    </header>
  );
}

export default Navbar;
