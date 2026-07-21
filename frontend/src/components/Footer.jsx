import { FiShield } from "react-icons/fi";

function Footer() {
  return (
    <footer className="border-t border-border">
      <div className="mx-auto max-w-6xl px-6 py-10 text-center">
        <div className="flex items-center justify-center gap-2">
          <FiShield className="text-primary" size={18} />
          <span className="font-bold text-white">VendorGuard AI</span>
        </div>
        <p className="mt-2 text-sm text-muted">
          AI-Powered Continuous Third-Party Vendor Risk Intelligence Platform
        </p>
        <p className="mt-1 text-xs text-slate-500">Prototype Version</p>
      </div>
    </footer>
  );
}

export default Footer;
