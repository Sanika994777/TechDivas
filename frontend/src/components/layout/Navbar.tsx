import { useState } from "react";
import { NavLink, Link, useNavigate } from "react-router-dom";
import {
  Menu, X, ChevronDown, User, LogOut, FileText, Map,
  Clipboard, Search, ShieldCheck, Wrench,
} from "lucide-react";
import { ChakraIcon } from "@/components/shared/ChakraIcon";
import { useAuth } from "@/context/AuthContext";
import { cn } from "@/lib/utils";

const CITIZEN_NAV = [
  { to: "/", label: "Home", end: true },
  { to: "/report", label: "Report Issue" },
  { to: "/nearby", label: "Nearby" },
  { to: "/my-complaints", label: "My Complaints" },
  { to: "/track", label: "Track Complaint" },
];

export function Navbar() {
  const [open, setOpen] = useState(false);
  const [lang, setLang] = useState<"EN" | "HI">("EN");
  const { user, logout } = useAuth();

  const isWorker = user?.role === "worker";
  const isAdmin  = user?.role === "admin";

  // Build nav links based on role
  const navLinks = isAdmin || isWorker ? [] : CITIZEN_NAV;

  return (
    <header className="sticky top-0 z-30 bg-white shadow-sm">
      {/* Tricolour strip */}
      <div className="tricolour-strip" aria-hidden="true" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 flex items-center justify-between h-16">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 flex-shrink-0 group" aria-label="CivicFix Home">
          <ChakraIcon size={32} color="#000080" className="group-hover:rotate-12 transition-transform duration-300" />
          <div>
            <span className="font-heading font-bold text-navy text-xl leading-tight">CivicFix</span>
            <span className="block text-[10px] text-gray-400 font-body leading-tight tracking-wide">
              Report. Track. Resolve.
            </span>
          </div>
        </Link>

        {/* Desktop nav */}
        <nav className="hidden md:flex items-center gap-1" aria-label="Main navigation">
          {navLinks.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.end}
              className={({ isActive }) =>
                cn(
                  "px-3 py-2 rounded-lg text-sm font-medium font-body transition-colors",
                  isActive
                    ? "bg-saffron-50 text-saffron-dark font-semibold"
                    : "text-navy-900 hover:bg-gray-100"
                )
              }
            >
              {l.label}
            </NavLink>
          ))}

          {/* Role-based dashboard links */}
          {isWorker && (
            <NavLink
              to="/worker"
              className={({ isActive }) =>
                cn(
                  "px-3 py-2 rounded-lg text-sm font-medium font-body transition-colors",
                  isActive ? "bg-saffron-50 text-saffron-dark font-semibold" : "text-navy-900 hover:bg-gray-100"
                )
              }
            >
              My Tasks
            </NavLink>
          )}
          {isAdmin && (
            <>
              <NavLink
                to="/admin"
                className={({ isActive }) =>
                  cn(
                    "px-3 py-2 rounded-lg text-sm font-medium font-body transition-colors",
                    isActive ? "bg-saffron-50 text-saffron-dark font-semibold" : "text-navy-900 hover:bg-gray-100"
                  )
                }
              >
                Issues
              </NavLink>
              <NavLink
                to="/worker"
                className={({ isActive }) =>
                  cn(
                    "px-3 py-2 rounded-lg text-sm font-medium font-body transition-colors",
                    isActive ? "bg-saffron-50 text-saffron-dark font-semibold" : "text-navy-900 hover:bg-gray-100"
                  )
                }
              >
                Worker View
              </NavLink>
            </>
          )}
        </nav>

        {/* Right side */}
        <div className="flex items-center gap-2">
          {/* Language toggle */}
          <button
            onClick={() => setLang(lang === "EN" ? "HI" : "EN")}
            className="hidden sm:flex items-center text-xs font-semibold text-gray-500 border border-gray-200 rounded-badge px-2 py-1 hover:border-navy transition-colors"
            aria-label={`Switch to ${lang === "EN" ? "हिंदी" : "English"}`}
          >
            {lang === "EN" ? "EN | हिं" : "हिं | EN"}
          </button>

          {/* Role-based action button */}
          {isAdmin && (
            <Link
              to="/admin"
              className="hidden sm:flex items-center gap-1.5 bg-saffron text-navy-900 text-sm font-semibold px-4 py-2 rounded-badge hover:bg-saffron-dark transition-colors min-h-[44px]"
            >
              <ShieldCheck size={14} /> Admin
            </Link>
          )}
          {isWorker && (
            <Link
              to="/worker"
              className="hidden sm:flex items-center gap-1.5 bg-navy text-white text-sm font-semibold px-4 py-2 rounded-badge hover:bg-navy-900 transition-colors min-h-[44px]"
            >
              <Wrench size={14} /> My Tasks
            </Link>
          )}
          {!isAdmin && !isWorker && (
            <Link
              to="/admin"
              className="hidden sm:flex items-center gap-1.5 bg-saffron text-navy-900 text-sm font-semibold px-4 py-2 rounded-badge hover:bg-saffron-dark transition-colors min-h-[44px]"
            >
              <ShieldCheck size={14} /> Admin
            </Link>
          )}

          {/* Auth */}
          {user ? (
            <UserMenu name={user.name} role={user.role} onLogout={logout} />
          ) : (
            <Link
              to="/login"
              className="hidden sm:flex items-center gap-1.5 bg-navy text-white text-sm font-semibold px-4 py-2 rounded-badge hover:bg-navy/90 transition-colors min-h-[44px]"
            >
              <User size={14} /> Sign In
            </Link>
          )}

          {/* Hamburger */}
          <button
            className="md:hidden p-2 rounded-lg hover:bg-gray-100 text-navy-900 min-h-[44px] min-w-[44px] flex items-center justify-center"
            onClick={() => setOpen(!open)}
            aria-expanded={open}
            aria-label="Toggle menu"
          >
            {open ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {open && (
        <div className="md:hidden bg-white border-t border-gray-100 px-4 pb-4 pt-2 space-y-1 shadow-lg">
          {navLinks.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.end}
              onClick={() => setOpen(false)}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 px-3 py-3 rounded-lg text-sm font-medium w-full",
                  isActive ? "bg-saffron-50 text-saffron-dark font-semibold" : "text-navy-900 hover:bg-gray-50"
                )
              }
            >
              {l.label}
            </NavLink>
          ))}

          {isWorker && (
            <NavLink to="/worker" onClick={() => setOpen(false)}
              className={({ isActive }) => cn("flex items-center gap-3 px-3 py-3 rounded-lg text-sm font-medium w-full",
                isActive ? "bg-saffron-50 text-saffron-dark font-semibold" : "text-navy-900 hover:bg-gray-50")}
            >
              <Wrench size={16} /> My Tasks
            </NavLink>
          )}
          {isAdmin && (
            <>
              <NavLink to="/admin" onClick={() => setOpen(false)}
                className={({ isActive }) => cn("flex items-center gap-3 px-3 py-3 rounded-lg text-sm font-medium w-full",
                  isActive ? "bg-saffron-50 text-saffron-dark font-semibold" : "text-navy-900 hover:bg-gray-50")}
              >
                <ShieldCheck size={16} /> Admin Panel
              </NavLink>
              <NavLink to="/worker" onClick={() => setOpen(false)}
                className={({ isActive }) => cn("flex items-center gap-3 px-3 py-3 rounded-lg text-sm font-medium w-full",
                  isActive ? "bg-saffron-50 text-saffron-dark font-semibold" : "text-navy-900 hover:bg-gray-50")}
              >
                <Wrench size={16} /> Worker View
              </NavLink>
            </>
          )}

          <div className="pt-2 border-t border-gray-100 flex flex-col gap-2">
            {!user && (
              <Link
                to="/login"
                onClick={() => setOpen(false)}
                className="flex items-center justify-center gap-2 bg-navy text-white text-sm font-semibold py-2.5 rounded-badge"
              >
                <User size={14} /> Sign In
              </Link>
            )}
            <button
              onClick={() => setLang(lang === "EN" ? "HI" : "EN")}
              className="border border-gray-200 text-xs font-semibold text-gray-500 px-3 py-2 rounded-badge"
            >
              {lang === "EN" ? "हिं" : "EN"}
            </button>
          </div>
        </div>
      )}
    </header>
  );
}

function UserMenu({ name, role, onLogout }: { name: string; role: string; onLogout: () => void }) {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();

  function handleLogout() {
    setOpen(false);
    onLogout();
    navigate("/");
  }

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 text-sm font-medium text-navy-900 hover:bg-gray-100 px-3 py-2 rounded-lg min-h-[44px]"
      >
        <span className="w-8 h-8 bg-saffron-50 rounded-full flex items-center justify-center font-heading font-bold text-saffron-dark">
          {name.charAt(0).toUpperCase()}
        </span>
        {name.split(" ")[0]}
        <ChevronDown size={14} className={cn("transition-transform", open ? "rotate-180" : "")} />
      </button>
      {open && (
        <div className="absolute right-0 top-full mt-1 bg-white border border-gray-100 rounded-card shadow-card-hover w-52 py-1 z-50">
          <div className="px-4 py-2 border-b border-gray-50">
            <p className="text-xs text-gray-400 font-semibold uppercase tracking-wider">{role}</p>
            <p className="text-sm text-navy-900 font-semibold truncate">{name}</p>
          </div>

          {role === "citizen" && (
            <Link to="/my-complaints" onClick={() => setOpen(false)} className="flex items-center gap-2 px-4 py-2 text-sm text-navy-900 hover:bg-gray-50">
              <Clipboard size={14} /> My Complaints
            </Link>
          )}
          {role === "worker" && (
            <Link to="/worker" onClick={() => setOpen(false)} className="flex items-center gap-2 px-4 py-2 text-sm text-navy-900 hover:bg-gray-50">
              <Wrench size={14} /> My Tasks
            </Link>
          )}
          {role === "admin" && (
            <>
              <Link to="/admin" onClick={() => setOpen(false)} className="flex items-center gap-2 px-4 py-2 text-sm text-navy-900 hover:bg-gray-50">
                <ShieldCheck size={14} /> Admin Panel
              </Link>
              <Link to="/worker" onClick={() => setOpen(false)} className="flex items-center gap-2 px-4 py-2 text-sm text-navy-900 hover:bg-gray-50">
                <Wrench size={14} /> Worker View
              </Link>
            </>
          )}

          <hr className="my-1 border-gray-100" />
          <button onClick={handleLogout} className="flex items-center gap-2 px-4 py-2 text-sm text-red-600 hover:bg-red-50 w-full">
            <LogOut size={14} /> Sign Out
          </button>
        </div>
      )}
    </div>
  );
}

// ─── Mobile bottom tab bar ────────────────────────────────────────────────────

export function MobileTabBar() {
  const { user } = useAuth();
  const isWorker = user?.role === "worker";
  const isAdmin  = user?.role === "admin";

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-30 md:hidden bg-white border-t border-gray-100 shadow-lg mobile-nav-safe"
      aria-label="Mobile navigation"
    >
      <div className="flex items-end justify-around px-2 pt-2 pb-2">
        <TabItem to="/" icon={<Map size={20} />} label="Home" end />
        <TabItem to="/nearby" icon={<Search size={20} />} label="Nearby" />
        {/* Centre button */}
        <div className="flex flex-col items-center -mt-5">
          <NavLink
            to={isAdmin ? "/admin" : isWorker ? "/worker" : "/report"}
            className={cn(
              "w-14 h-14 rounded-full flex items-center justify-center shadow-lg transition-colors active:scale-95",
              isAdmin ? "bg-saffron hover:bg-saffron-dark" : isWorker ? "bg-navy hover:bg-navy-900" : "bg-saffron hover:bg-saffron-dark"
            )}
            aria-label={isAdmin ? "Admin Panel" : isWorker ? "My Tasks" : "Report an issue"}
          >
            {isAdmin
              ? <ShieldCheck size={22} className="text-white" />
              : isWorker
              ? <Wrench size={22} className="text-white" />
              : <FileText size={22} className="text-white" />}
          </NavLink>
          <span className="text-[10px] mt-1 text-gray-500 font-body">
            {isAdmin ? "Admin" : isWorker ? "Tasks" : "Report"}
          </span>
        </div>
        <TabItem to="/my-complaints" icon={<Clipboard size={20} />} label="Mine" />
        <TabItem to="/track" icon={<Search size={20} />} label="Track" />
      </div>
    </nav>
  );
}

function TabItem({ to, icon, label, end }: { to: string; icon: React.ReactNode; label: string; end?: boolean }) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        cn(
          "flex flex-col items-center gap-0.5 px-3 py-1 rounded-lg min-w-[44px] transition-colors",
          isActive ? "text-saffron-dark" : "text-gray-400 hover:text-gray-600"
        )
      }
    >
      {icon}
      <span className="text-[10px] font-body">{label}</span>
    </NavLink>
  );
}
