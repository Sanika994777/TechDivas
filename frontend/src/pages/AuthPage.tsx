import { useState, useEffect } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { Eye, EyeOff, Loader2, CheckCircle } from "lucide-react";
import { ChakraIcon } from "@/components/shared/ChakraIcon";
import { login as apiLogin, register as apiRegister, BASE_URL } from "@/api/client";
import { useAuth } from "@/context/AuthContext";
import { cn } from "@/lib/utils";

interface AuthPageProps {
  mode?: "login" | "register";
}

export function AuthPage({ mode = "login" }: AuthPageProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const auth = useAuth();
  const isRegister = mode === "register" || location.pathname === "/register";
  // Where to go after login — default to "/"
  const from = (location.state as { from?: string })?.from ?? "/";

  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [showPw, setShowPw] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [serverReady, setServerReady] = useState(true);

  // Pre-emptively wake the Render backend while the user types credentials
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 10_000);
        await fetch(`${BASE_URL}/health`, { signal: controller.signal });
        clearTimeout(timer);
        if (!cancelled) setServerReady(true);
      } catch {
        // Server is cold — it's fine, the retry logic in apiFetch will handle it
        if (!cancelled) setServerReady(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  function validate() {
    const e: Record<string, string> = {};
    if (isRegister && form.name.trim().length < 2) e.name = "Name must be at least 2 characters.";
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) e.email = "Enter a valid email address.";
    if (isRegister && form.password.length < 8) {
      e.password = "Password must be at least 8 characters.";
    } else if (!isRegister && !form.password) {
      e.password = "Please enter your password.";
    }
    setErrors(e);
    return Object.keys(e).length === 0;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;
    setLoading(true);
    setErrors({});
    try {
      if (isRegister) {
        const res = await apiRegister(form.name, form.email, form.password);
        auth.login(
          { name: res.user?.name ?? form.name, email: res.user?.email ?? form.email, role: (res.role ?? "citizen") as "citizen" | "worker" | "admin" },
          res.token
        );
        setSuccess(true);
        setTimeout(() => navigate(from, { replace: true }), 800);
      } else {
        const res = await apiLogin(form.email, form.password);
        const role = (res.role ?? "citizen") as "citizen" | "worker" | "admin";
        auth.login(
          { name: res.user?.name ?? form.email.split("@")[0].replace(/[._]/g, " "), email: res.user?.email ?? form.email, role },
          res.token
        );
        setSuccess(true);
        let target = from;
        if (target === "/") {
          if (role === "admin") target = "/admin";
          else if (role === "worker") target = "/worker";
        }
        setTimeout(() => navigate(target, { replace: true }), 800);
      }
    } catch (err: unknown) {
      let msg = "Something went wrong. Please try again.";
      if (err instanceof Error) {
        if (err.message.includes("Invalid") || err.message.includes("credentials")) {
          msg = "Invalid email or password. Please check your credentials.";
        } else if (err.message.includes("already registered")) {
          msg = "This email is already registered. Please sign in instead.";
        } else if (err.name === "AbortError" || err.message.includes("abort")) {
          msg = "The server is still waking up (free-tier hosting). Please wait 30 seconds and try again.";
          setServerReady(false);
        } else if (err.message.includes("Failed to fetch") || err.message.includes("NetworkError") || err.message.includes("Load failed")) {
          msg = "Unable to reach the server. It may be starting up — please refresh the page and try again in a moment.";
          setServerReady(false);
        } else {
          msg = err.message;
        }
      }
      setErrors({ form: msg });
    } finally {
      setLoading(false);
    }
  }

  function field(id: string, label: string, type: string, value: string, onChange: (v: string) => void, extra?: React.ReactNode) {
    return (
      <div>
        <label htmlFor={id} className="block text-sm font-semibold text-navy-900 mb-1.5 font-body">
          {label}
        </label>
        <div className="relative">
          <input
            id={id}
            type={type}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            className={cn(
              "w-full border rounded-input px-4 py-3 text-sm font-body bg-white focus:outline-none focus:ring-2 focus:ring-navy/40 transition-shadow",
              errors[id.replace("-", "")] ? "border-red-400 bg-red-50" : "border-gray-200 hover:border-gray-300"
            )}
            aria-invalid={!!errors[id]}
            aria-describedby={errors[id] ? `${id}-error` : undefined}
          />
          {extra}
        </div>
        {errors[id] && (
          <p id={`${id}-error`} className="text-xs text-red-600 mt-1 font-body" role="alert">
            {errors[id]}
          </p>
        )}
      </div>
    );
  }

  return (
    <main className="min-h-screen flex bg-white">
      {/* Left navy panel */}
      <div className="hidden lg:flex lg:flex-1 bg-navy flex-col items-center justify-center px-12 relative overflow-hidden">
        {/* Background chakras */}
        <ChakraIcon size={240} color="rgba(255,255,255,0.04)" className="absolute top-8 right-8" />
        <ChakraIcon size={160} color="rgba(255,255,255,0.04)" className="absolute bottom-12 left-6" />
        {/* Content */}
        <div className="relative z-10 text-center text-white max-w-sm">
          <ChakraIcon size={72} color="white" className="mx-auto mb-6" />
          <h1 className="font-heading font-bold text-3xl mb-4">CivicFix</h1>
          <p className="text-white/70 leading-relaxed mb-8">
            Join thousands of Pune citizens who report local issues and make their neighbourhoods better — one complaint at a time.
          </p>
          {/* Pledge */}
          <div className="bg-white/10 rounded-card p-5 text-left border border-white/20">
            <p className="text-white/90 text-sm leading-relaxed italic">
              "I pledge to report civic issues responsibly, provide accurate information, and work together with my community for a better Pune."
            </p>
          </div>
          {/* Tricolour strip */}
          <div className="tricolour-strip mt-8 rounded-badge opacity-60" />
        </div>
      </div>

      {/* Right form panel */}
      <div className="flex-1 flex flex-col items-center justify-center px-6 py-12 max-w-xl w-full mx-auto">
        {/* Mobile logo */}
        <Link to="/" className="flex lg:hidden items-center gap-2 mb-8">
          <ChakraIcon size={28} color="#000080" />
          <span className="font-heading font-bold text-navy text-xl">CivicFix</span>
        </Link>

        {success ? (
          <div className="text-center">
            <CheckCircle size={56} className="text-green mx-auto mb-4" />
            <h2 className="font-heading font-bold text-2xl text-navy mb-2">
              {isRegister ? "Account Created!" : "Welcome back!"}
            </h2>
            <p className="text-gray-500">Redirecting…</p>
          </div>
        ) : (
          <div className="w-full max-w-sm">
            <h2 className="font-heading font-bold text-2xl text-navy mb-1">
              {isRegister ? "Create your account" : "Sign in to CivicFix"}
            </h2>
            <p className="text-gray-500 text-sm mb-8 font-body">
              {isRegister
                ? "Report issues and track their resolution in Pune."
                : "Welcome back. Your city needs you."}
            </p>

            {!serverReady && (
              <div className="bg-amber-50 border border-amber-200 rounded-input px-4 py-3 text-sm text-amber-700 mb-4 flex items-center gap-2" role="status">
                <Loader2 size={16} className="animate-spin flex-shrink-0" />
                <span>Our server is waking up — first sign-in may take a moment. Please wait…</span>
              </div>
            )}

            {errors.form && (
              <div className="bg-red-50 border border-red-200 rounded-input px-4 py-3 text-sm text-red-700 mb-4" role="alert">
                {errors.form}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4" noValidate>
              {isRegister && field(
                "name", "Full Name", "text", form.name,
                (v) => setForm((f) => ({ ...f, name: v }))
              )}
              {field("email", "Email Address", "email", form.email, (v) => setForm((f) => ({ ...f, email: v })))}
              {field(
                "password", "Password",
                showPw ? "text" : "password",
                form.password,
                (v) => setForm((f) => ({ ...f, password: v })),
                <button
                  type="button"
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  onClick={() => setShowPw(!showPw)}
                  aria-label={showPw ? "Hide password" : "Show password"}
                >
                  {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-saffron text-navy-900 font-heading font-semibold py-3.5 rounded-badge hover:bg-saffron-dark transition-colors disabled:opacity-60 flex items-center justify-center gap-2 min-h-[52px]"
              >
                {loading ? <Loader2 size={18} className="animate-spin" /> : null}
                {isRegister ? "Create Account" : "Sign In"}
              </button>
            </form>

            <p className="text-center text-sm text-gray-500 mt-6 font-body">
              {isRegister ? "Already have an account?" : "New to CivicFix?"}{" "}
              <Link
                to={isRegister ? "/login" : "/register"}
                className="text-navy font-semibold hover:text-saffron-dark transition-colors"
              >
                {isRegister ? "Sign in" : "Create account"}
              </Link>
            </p>

            {!isRegister && (
              <div className="mt-6 pt-5 border-t border-gray-100">
                <p className="text-xs font-semibold text-gray-500 mb-2.5 uppercase tracking-wider text-center">
                  Quick Demo Accounts (Autofill)
                </p>
                <div className="grid grid-cols-3 gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      setForm({ name: "", email: "citizen@demo.com", password: "Demo@1234" });
                      setErrors({});
                    }}
                    className="px-2 py-1.5 text-xs font-medium border border-gray-200 rounded-lg hover:border-navy hover:text-navy hover:bg-navy/5 transition-colors text-center"
                  >
                    Citizen
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setForm({ name: "", email: "worker@demo.com", password: "Demo@1234" });
                      setErrors({});
                    }}
                    className="px-2 py-1.5 text-xs font-medium border border-gray-200 rounded-lg hover:border-navy hover:text-navy hover:bg-navy/5 transition-colors text-center"
                  >
                    Worker
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setForm({ name: "", email: "admin@demo.com", password: "Demo@1234" });
                      setErrors({});
                    }}
                    className="px-2 py-1.5 text-xs font-medium border border-gray-200 rounded-lg hover:border-navy hover:text-navy hover:bg-navy/5 transition-colors text-center"
                  >
                    Admin
                  </button>
                </div>
                <p className="text-[11px] text-gray-400 text-center mt-2">
                  Password: <code className="bg-gray-100 px-1 py-0.5 rounded text-gray-600 font-mono">Demo@1234</code>
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </main>
  );
}
