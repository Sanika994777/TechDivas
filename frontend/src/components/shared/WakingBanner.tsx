import { useEffect, useState } from "react";
import { onWakingChange } from "@/api/client";
import { Loader2 } from "lucide-react";

/**
 * Banner shown when the backend is slow to respond (e.g. cold start).
 * Subscribes to the waking state emitted by the API client.
 */
export function WakingBanner() {
  const [waking, setWaking] = useState(false);

  useEffect(() => {
    const unsub = onWakingChange(setWaking);
    return unsub;
  }, []);

  if (!waking) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed top-16 inset-x-0 z-50 flex items-center justify-center px-4 py-2 bg-saffron-50 border-b border-saffron/30"
    >
      <Loader2 size={14} className="animate-spin text-saffron-dark mr-2 flex-shrink-0" />
      <p className="text-sm text-saffron-dark font-body">
        Server is waking up — retrying automatically…
      </p>
    </div>
  );
}
