import { Link, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarRail,
  SidebarSeparator,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import {
  Cable,
  Database,
  LayoutDashboard,
  Settings,
  Shuffle,
} from "lucide-react";

function ThemeToggle() {
  const [dark, setDark] = useState(false);
  useEffect(() => {
    const saved = localStorage.getItem("theme:dark");
    const isDark = saved ? saved === "true" : false;
    setDark(isDark);
    document.documentElement.classList.toggle("dark", isDark);
  }, []);
  return (
    <Button
      variant="ghost"
      size="sm"
      aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
      onClick={() => {
        const next = !dark;
        setDark(next);
        document.documentElement.classList.toggle("dark", next);
        localStorage.setItem("theme:dark", String(next));
      }}
    >
      {dark ? (
        <span className="text-lg">☀️</span>
      ) : (
        <span className="text-lg">🌙</span>
      )}
    </Button>
  );
}

function WindowControls() {
  return (
    <div className="flex items-center gap-2 mr-3">
      <span className="size-3 rounded-full bg-[#FF5F57] shadow" />
      <span className="size-3 rounded-full bg-[#FEBC2E] shadow" />
      <span className="size-3 rounded-full bg-[#28C840] shadow" />
    </div>
  );
}

export default function AppShell({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const isActive = (to: string) => location.pathname === to;
  const [_, setTick] = useState(0);
  const [searchEl, setSearchEl] = useState<HTMLInputElement | null>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        searchEl?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [searchEl]);

  return (
    <SidebarProvider>
      <Sidebar collapsible="icon" className="border-r border-sidebar-border">
        <SidebarHeader>
          <div className="flex items-center gap-2 px-2 py-1">
            <div className="h-8 w-8 rounded-lg bg-primary/10 flex items-center justify-center font-bold text-primary">
              C
            </div>
            <div className="text-sm font-semibold">Chroma Control</div>
          </div>
        </SidebarHeader>
        <SidebarContent>
          <SidebarGroup>
            <SidebarGroupLabel>Overview</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                <SidebarMenuItem>
                  <SidebarMenuButton asChild isActive={isActive("/")}>
                    <Link to="/">
                      <LayoutDashboard />
                      <span>Dashboard</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
                <SidebarMenuItem>
                  <SidebarMenuButton asChild isActive={isActive("/models")}>
                    <Link to="/models">
                      <Shuffle />
                      <span>Models</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    asChild
                    isActive={isActive("/connections")}
                  >
                    <Link to="/connections">
                      <Cable />
                      <span>Connections</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    asChild
                    isActive={isActive("/collections")}
                  >
                    <Link to="/collections">
                      <Database />
                      <span>Collections</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
          <SidebarSeparator />
          <SidebarGroup>
            <SidebarGroupLabel>System</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                <SidebarMenuItem>
                  <SidebarMenuButton asChild isActive={isActive("/settings")}>
                    <Link to="/settings">
                      <Settings />
                      <span>Settings</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        </SidebarContent>
        <SidebarFooter>
          <div className="text-[10px] text-sidebar-foreground/60 px-2">
            v1.0.0
          </div>
        </SidebarFooter>
        <SidebarRail />
      </Sidebar>
      <SidebarInset>
        <header className="sticky top-0 z-20 backdrop-blur supports-[backdrop-filter]:bg-background/70 border-b">
          <div className={cn("flex items-center gap-2 px-4", "h-14")}>
            <SidebarTrigger className="md:hidden" />
            <WindowControls />
            <div className="font-semibold tracking-tight">Chroma Control</div>
            <div className="ml-auto flex items-center gap-2">
              <div className="hidden md:block">
                <Input
                  placeholder="Search… (⌘K)"
                  className="h-9 w-64"
                  ref={setSearchEl}
                />
              </div>
              <ThemeToggle />
            </div>
          </div>
        </header>
        <div className="p-6 max-w-[1200px] w-full mx-auto">{children}</div>
      </SidebarInset>
    </SidebarProvider>
  );
}
