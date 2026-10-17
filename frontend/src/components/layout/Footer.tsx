import { Link } from "react-router-dom";
import { ChakraIcon } from "@/components/shared/ChakraIcon";
import { Phone, Mail, Github } from "lucide-react";

export function Footer() {
  return (
    <footer className="bg-navy-900 text-white/80 font-body mt-16">
      {/* Tricolour strip on top */}
      <div className="tricolour-strip" aria-hidden="true" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-12">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8 mb-10">
          {/* Brand */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <ChakraIcon size={28} color="white" />
              <span className="font-heading font-bold text-white text-lg">CivicFix</span>
            </div>
            <p className="text-sm text-white/60 leading-relaxed">
              A citizens' platform to report, track, and resolve local civic issues across Pune and beyond.
            </p>
            <p className="mt-4 text-xs text-white/40 italic">
              Made for a better Bharat 🇮🇳
            </p>
          </div>

          {/* Quick links */}
          <div>
            <h3 className="font-heading font-semibold text-white text-sm mb-3 uppercase tracking-wider">Quick Links</h3>
            <ul className="space-y-2 text-sm">
              {[
                { to: "/", label: "Home" },
                { to: "/report", label: "Report Issue" },
                { to: "/nearby", label: "Nearby Issues" },
                { to: "/track", label: "Track Complaint" },
              ].map((l) => (
                <li key={l.to}>
                  <Link to={l.to} className="hover:text-saffron transition-colors">
                    {l.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Categories */}
          <div>
            <h3 className="font-heading font-semibold text-white text-sm mb-3 uppercase tracking-wider">Categories</h3>
            <ul className="space-y-2 text-sm">
              {["🕳️ Pothole", "💧 Water Leak", "🗑️ Garbage", "💡 Streetlight", "📋 Other"].map((c) => (
                <li key={c}>
                  <Link to="/report" className="hover:text-saffron transition-colors">{c}</Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Contact */}
          <div>
            <h3 className="font-heading font-semibold text-white text-sm mb-3 uppercase tracking-wider">Helpline</h3>
            <ul className="space-y-2 text-sm">
              <li className="flex items-center gap-2">
                <Phone size={13} className="text-saffron flex-shrink-0" />
                <span>020-25506800 (PMC)</span>
              </li>
              <li className="flex items-center gap-2">
                <Phone size={13} className="text-saffron flex-shrink-0" />
                <span>1800-102-7788 (Toll Free)</span>
              </li>
              <li className="flex items-center gap-2">
                <Mail size={13} className="text-saffron flex-shrink-0" />
                <span>help@civicfix.in</span>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="border-t border-white/10 pt-6 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-white/40">
          <p>© 2026 CivicFix. Demo project — not an official PMC platform.</p>
          <div className="flex items-center gap-4">
            <a href="#" className="hover:text-white transition-colors">Privacy</a>
            <a href="#" className="hover:text-white transition-colors">Terms</a>
            <a href="#" className="hover:text-white transition-colors flex items-center gap-1">
              <Github size={12} /> GitHub
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
