import React from "react";
import "./global.css";

import { Toaster } from "@/components/ui/toaster";
import { createRoot } from "react-dom/client";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Index from "./pages/Index";
import NotFound from "./pages/NotFound";
import Placeholder from "./pages/Placeholder";
import ChromaKnowledgeBase from "./pages/ChromaKnowledgeBase";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<ChromaKnowledgeBase />} />
          <Route path="/models" element={<Placeholder title="Models" />} />
          <Route
            path="/connections"
            element={<Placeholder title="Connections" />}
          />
          <Route
            path="/collections"
            element={<Placeholder title="Collections" />}
          />
          <Route path="/settings" element={<Placeholder title="Settings" />} />
          {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

const container = document.getElementById("root")!;
const w = window as unknown as { __app_root?: ReturnType<typeof createRoot> };
if (!w.__app_root) {
  w.__app_root = createRoot(container);
}
w.__app_root.render(<App />);
