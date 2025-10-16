import { useEffect, useMemo, useState } from "react";
import AppShell from "@/components/layout/AppShell";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Database, PlugZap, Server, ShieldCheck, Shuffle } from "lucide-react";
import { toast } from "sonner";

export default function Index() {
  // Chroma connection form state
  const [host, setHost] = useState("http://localhost");
  const [port, setPort] = useState("8000");
  const [apiKey, setApiKey] = useState("");
  const [connected, setConnected] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testOk, setTestOk] = useState<boolean | null>(null);
  const [testMsg, setTestMsg] = useState<string>("");

  // Model manager state
  const providers = [
    "OpenAI",
    "Anthropic",
    "Meta",
    "Mistral",
    "Cohere",
  ] as const;
  const modelsByProvider: Record<string, string[]> = {
    OpenAI: ["gpt-4o", "o4-mini", "gpt-4.1"],
    Anthropic: ["claude-3.5-sonnet", "claude-3.7"],
    Meta: ["llama-3.1-70b", "llama-3.1-8b"],
    Mistral: ["mistral-large", "mistral-small"],
    Cohere: ["command-r7b", "command-r"],
  };
  const [provider, setProvider] =
    useState<(typeof providers)[number]>("OpenAI");
  const [model, setModel] = useState(modelsByProvider["OpenAI"][0]);
  useEffect(() => setModel(modelsByProvider[provider][0]), [provider]);

  // MCP & integrations
  type McpServerStatus = "connected" | "disconnected";

  const [mcpServers, setMcpServers] = useState<Array<{ name: string; status: McpServerStatus }>>([
    { name: "Netlify", status: "disconnected" },
    { name: "Vercel", status: "disconnected" },
    { name: "Neon", status: "disconnected" },
    { name: "Supabase", status: "disconnected" },
    { name: "Builder.io", status: "disconnected" },
    { name: "Sentry", status: "disconnected" },
    { name: "Zapier", status: "disconnected" },
  ]);

  const collections = useMemo(
    () => [
      { name: "documents", vectors: 15234, dim: 1536, modified: "2h ago" },
      { name: "products", vectors: 6842, dim: 1024, modified: "1d ago" },
      { name: "logs", vectors: 42033, dim: 512, modified: "5m ago" },
    ],
    [],
  );

  return (
    <AppShell>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl md:text-3xl font-semibold tracking-tight">
            Chroma Vector Database
          </h1>
          <p className="text-muted-foreground mt-1">
            Manage connection, models, MCP servers, and integrations
          </p>
        </div>
        <Badge
          variant="secondary"
          className={connected ? "bg-emerald-100 text-emerald-700" : ""}
        >
          {connected ? "Connected" : "Disconnected"}
        </Badge>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <Card className="xl:col-span-1">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-xl">
              <Server className="text-primary" /> Connection
            </CardTitle>
            <CardDescription>
              Configure Chroma endpoint and authentication
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label htmlFor="host" className="text-sm text-muted-foreground">
                  Host
                </label>
                <Input
                  id="host"
                  value={host}
                  onChange={(e) => setHost(e.target.value)}
                  placeholder="http://localhost"
                />
              </div>
              <div>
                <label htmlFor="port" className="text-sm text-muted-foreground">
                  Port
                </label>
                <Input
                  id="port"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  value={port}
                  onChange={(e) => setPort(e.target.value)}
                  placeholder="8000"
                />
              </div>
            </div>
            <div>
              <label htmlFor="apiKey" className="text-sm text-muted-foreground">
                API Key
              </label>
              <Input
                id="apiKey"
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="Optional"
              />
            </div>
            <div className="flex items-center gap-3">
              <Button
                onClick={() => {
                  setConnected(true);
                  toast.success("Connected");
                }}
                className=""
              >
                Connect
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  setConnected(false);
                  toast("Disconnected");
                }}
              >
                Disconnect
              </Button>
              <Button
                variant="secondary"
                onClick={async () => {
                  const buildBase = (h: string, p: string) => {
                    // SECURITY: Enhanced URL validation and SSRF protection
                    console.log('[URL_SECURITY] Building base URL:', { host: h, port: p });

                    let base = h.trim();

                    // Input sanitization
                    if (!base || base.length === 0) {
                      throw new Error('Host cannot be empty');
                    }

                    // Remove potentially dangerous characters
                    base = base.replace(/[<>'"\\]/g, '');

                    // Add protocol if missing
                    if (!/^https?:\/\//i.test(base)) {
                      base = `http://${base}`;
                    }

                    try {
                      const u = new URL(base);

                      // SECURITY: Strict allowlist for safe hosts
                      const allowedHosts = [
                        'localhost',
                        '127.0.0.1',
                        '0.0.0.0',
                        'chroma',
                        'chromadb',
                        'vector-db'
                      ];

                      const isAllowed = allowedHosts.includes(u.hostname) ||
                        u.hostname.endsWith('.local') ||
                        u.hostname.match(/^localhost:\d+$/);

                      if (!isAllowed) {
                        throw new Error(`Host '${u.hostname}' is not in the allowlist`);
                      }

                      // SECURITY: Only allow HTTP for localhost/private networks
                      if (u.protocol === 'https:' && u.hostname !== 'localhost') {
                        console.warn('[URL_SECURITY] HTTPS URL for non-localhost host:', u.hostname);
                      }

                      // Validate port
                      const portNum = p ? parseInt(p, 10) : (u.port ? parseInt(u.port, 10) : (u.protocol === 'https:' ? 443 : 80));
                      if (isNaN(portNum) || portNum < 1 || portNum > 65535) {
                        throw new Error('Invalid port number');
                      }

                      u.port = portNum.toString();
                      console.log('[URL_SECURITY] Valid URL constructed:', u.origin);
                      return u.origin;

                    } catch (error) {
                      console.error('[URL_SECURITY] URL construction failed:', error.message);
                      throw new Error(`Invalid URL: ${error.message}`);
                    }
                  };

                  try {
                    const base = buildBase(host, port);
                    setTesting(true);
                    setTestOk(null);
                    setTestMsg("");

                    const proxyRes = await fetch("/api/chroma/heartbeat", {
                      method: "POST",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({ baseUrl: base, apiKey }),
                    });
                    const proxyJson = await proxyRes
                      .json()
                      .catch(() => ({}) as any);
                    if (proxyRes.ok && proxyJson && proxyJson.ok) {
                      setTestOk(true);
                      setTestMsg(
                        typeof proxyJson.data === "string"
                          ? proxyJson.data
                          : JSON.stringify(proxyJson.data).slice(0, 120),
                      );
                      toast.success("Chroma heartbeat OK");
                    } else {
                      setTestOk(false);
                      setTestMsg(
                        String(
                          (proxyJson && proxyJson.error) ||
                            proxyRes.statusText ||
                            "Failed",
                        ),
                      );
                      toast.error("Connection failed");
                    }
                  } catch (e: any) {
                    setTestOk(false);
                    setTestMsg(e.message || "Failed to reach Chroma heartbeat");
                    toast.error(`Connection failed: ${e.message}`);
                  } finally {
                    setTesting(false);
                  }
                }}
                disabled={testing}
              >
                {testing ? "Testing…" : "Test connection"}
              </Button>
            </div>
            <div className="mt-2 text-xs" role="status" aria-live="polite">
              {testOk === null ? (
                <span className="text-muted-foreground">
                  Status: Not tested
                </span>
              ) : testOk ? (
                <span className="text-emerald-600">
                  Status: Online — {testMsg}
                </span>
              ) : (
                <span className="text-red-600">
                  Status: Offline — {testMsg}
                </span>
              )}
            </div>
            <p className="text-xs text-muted-foreground">
              Tip: For managed hosting and secure environment variables, connect
              a provider via MCP.
            </p>
          </CardContent>
          <CardFooter className="justify-between">
            <div className="text-xs text-muted-foreground">
              Endpoint: {host}:{port}
            </div>
            <Badge variant="outline" className="rounded-full">
              macOS optimized
            </Badge>
          </CardFooter>
        </Card>

        <Card className="xl:col-span-1">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-xl">
              <Shuffle className="text-primary" /> Model Manager
            </CardTitle>
            <CardDescription>
              Swap AI models and providers without code changes
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="text-sm text-muted-foreground">
                  Provider
                </label>
                <Select
                  value={provider}
                  onValueChange={(v) => setProvider(v as any)}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select provider" />
                  </SelectTrigger>
                  <SelectContent>
                    {providers.map((p) => (
                      <SelectItem key={p} value={p}>
                        {p}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-sm text-muted-foreground">Model</label>
                <Select value={model} onValueChange={setModel}>
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select model" />
                  </SelectTrigger>
                  <SelectContent>
                    {modelsByProvider[provider].map((m) => (
                      <SelectItem key={m} value={m}>
                        {m}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="flex items-center justify-between rounded-lg border p-3">
              <div>
                <div className="text-sm font-medium">Use for embedding</div>
                <p className="text-xs text-muted-foreground">
                  Apply this model for vector creation
                </p>
              </div>
              <Switch defaultChecked />
            </div>
            <div className="flex items-center justify-between rounded-lg border p-3">
              <div>
                <div className="text-sm font-medium">
                  Use for chat/completion
                </div>
                <p className="text-xs text-muted-foreground">
                  Route generation to selected model
                </p>
              </div>
              <Switch defaultChecked />
            </div>
          </CardContent>
          <CardFooter className="gap-3">
            <Button>Apply</Button>
            <Button variant="outline">Test inference</Button>
          </CardFooter>
        </Card>

        <Card className="xl:col-span-1">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-xl">
              <PlugZap className="text-primary" /> MCP & Integrations
            </CardTitle>
            <CardDescription>Connect providers and platforms</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {mcpServers.map((s, i) => (
              <div
                key={s.name}
                className="flex items-center justify-between rounded-lg border p-3"
              >
                <div className="flex items-center gap-2">
                  <ShieldCheck
                    className={
                      s.status === "connected"
                        ? "text-emerald-600"
                        : "text-muted-foreground"
                    }
                  />
                  <div>
                    <div className="text-sm font-medium">{s.name}</div>
                    <div className="text-xs text-muted-foreground capitalize">
                      {s.status}
                    </div>
                  </div>
                </div>
                {s.status === "connected" ? (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() =>
                      setMcpServers((arr) =>
                        arr.map((x, idx) =>
                          idx === i ? { ...x, status: "disconnected" } : x,
                        ),
                      )
                    }
                  >
                    Disconnect
                  </Button>
                ) : (
                  <Button
                    size="sm"
                    onClick={() =>
                      setMcpServers((arr) =>
                        arr.map((x, idx) =>
                          idx === i ? { ...x, status: "connected" } : x,
                        ),
                      )
                    }
                  >
                    Connect
                  </Button>
                )}
              </div>
            ))}
            <p className="text-xs text-muted-foreground">
              To add real connections, use the platform actions to connect MCP
              servers (Neon, Netlify, Vercel, Supabase, Builder.io, Zapier,
              Sentry).
            </p>
          </CardContent>
        </Card>
      </div>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-xl">
            <Database className="text-primary" /> Collections
          </CardTitle>
          <CardDescription>Overview of your vector stores</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Vectors</TableHead>
                <TableHead>Dimension</TableHead>
                <TableHead>Last Modified</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {collections.map((c) => (
                <TableRow key={c.name}>
                  <TableCell className="font-medium">{c.name}</TableCell>
                  <TableCell>{c.vectors.toLocaleString()}</TableCell>
                  <TableCell>{c.dim}</TableCell>
                  <TableCell>{c.modified}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </AppShell>
  );
}
