import { createFileRoute } from "@tanstack/react-router";
import { Share2 } from "lucide-react";

import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";

export const Route = createFileRoute("/graph")({
  head: () => ({
    meta: [
      { title: "Knowledge Graph — SETU" },
      {
        name: "description",
        content:
          "Visualize equipment, documents, and incidents as a connected knowledge graph.",
      },
    ],
  }),
  component: GraphPage,
});

function GraphPage() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-6 md:px-8 md:py-10">
      <PageHeader
        title="Knowledge graph"
        description="A live view of equipment, documents, work orders, and incidents as a connected graph."
      />
      <EmptyState
        icon={<Share2 className="h-5 w-5" />}
        title="Graph endpoint not available yet"
        description="This screen is waiting on the backend to expose a graph export endpoint (e.g. GET /graph/export). Once available, nodes will be color-coded by entity type and interactively explorable."
      />
    </div>
  );
}
