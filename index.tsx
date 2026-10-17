import { createFileRoute } from "@tanstack/react-router";
import { HomePage } from "@/components/civicfix/pages";

export const Route = createFileRoute("/")({
  head: () => ({ meta: [
    { title: "CivicFix Pune | Report. Track. Resolve." },
    { name: "description", content: "Report local issues, connect with your neighbours, and follow progress toward a better Pune." },
    { property: "og:title", content: "CivicFix Pune | Report. Track. Resolve." },
    { property: "og:description", content: "Help make Pune a better place to live. Report civic issues and follow every step toward a fix." },
    { property: "og:type", content: "website" },
    { name: "twitter:card", content: "summary_large_image" },
  ] }),
  component: HomePage,
});