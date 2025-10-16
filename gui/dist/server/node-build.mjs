import path from "path";
import * as express from "express";
import express__default from "express";
import cors from "cors";
import { spawn } from "child_process";
import fs from "fs";
import os from "os";
import { fileURLToPath } from "url";
const __filename = fileURLToPath(import.meta.url);
const __dirname$1 = path.dirname(__filename);
const PORT = process.env.PORT || 3001;
function createServer() {
  const app2 = express__default();
  app2.use(cors());
  app2.use(express__default.json());
  app2.get("/api/health", (req, res) => {
    res.json({
      status: "healthy",
      timestamp: (/* @__PURE__ */ new Date()).toISOString(),
      service: "Awakened Mind GUI API"
    });
  });
  app2.get("/api/system/status", async (req, res) => {
    try {
      const pythonScript = path.join(__dirname$1, "../../core/check_status.py");
      const pythonProcess = spawn("python3", [pythonScript]);
      let stdout = "";
      let stderr = "";
      pythonProcess.stdout.on("data", (data) => {
        stdout += data.toString();
      });
      pythonProcess.stderr.on("data", (data) => {
        stderr += data.toString();
      });
      pythonProcess.on("close", (code) => {
        if (code === 0) {
          try {
            const status = JSON.parse(stdout);
            res.json(status);
          } catch (parseError) {
            res.status(500).json({
              error: "Failed to parse system status",
              details: parseError.message
            });
          }
        } else {
          res.status(500).json({
            error: "System status check failed",
            details: stderr
          });
        }
      });
    } catch (error) {
      res.status(500).json({
        error: "Failed to execute system status check",
        details: error.message
      });
    }
  });
  app2.post("/api/knowledge/search", async (req, res) => {
    try {
      const { query, collection = "technical_docs", limit = 10 } = req.body;
      if (!query || typeof query !== "string") {
        return res.status(400).json({ error: "Query parameter must be a non-empty string" });
      }
      if (query.length > 1e3) {
        return res.status(400).json({ error: "Query parameter too long (max 1000 characters)" });
      }
      const sanitizedQuery = query.replace(/['"`;\\]/g, "").trim();
      if (sanitizedQuery.length === 0) {
        return res.status(400).json({ error: "Query contains only invalid characters" });
      }
      if (collection && typeof collection !== "string") {
        return res.status(400).json({ error: "Collection parameter must be a string" });
      }
      const sanitizedCollection = (collection || "technical_docs").replace(/[^a-zA-Z0-9_-]/g, "");
      if (sanitizedCollection.length === 0) {
        return res.status(400).json({ error: "Invalid collection name format" });
      }
      if (limit && (typeof limit !== "number" || limit < 1 || limit > 100)) {
        return res.status(400).json({ error: "Limit must be a number between 1 and 100" });
      }
      const safeLimit = Math.min(Math.max(limit || 10, 1), 100);
      console.log("[SEARCH_SECURITY] Sanitized search request:", {
        originalQuery: query.substring(0, 100) + (query.length > 100 ? "..." : ""),
        sanitizedQuery: sanitizedQuery.substring(0, 100) + (sanitizedQuery.length > 100 ? "..." : ""),
        collection: sanitizedCollection,
        limit: safeLimit,
        queryLength: query.length,
        sanitizedLength: sanitizedQuery.length
      });
      const searchScript = `
import asyncio
import sys
import json
import os
from core.chroma_connection import NHBKnowledgeBase

async def search_knowledge():
    try:
        # Get parameters from environment variables (safer than string interpolation)
        collection = os.environ.get('SEARCH_COLLECTION', 'technical_docs')
        query = os.environ.get('SEARCH_QUERY', '')
        limit = int(os.environ.get('SEARCH_LIMIT', '10'))

        kb = NHBKnowledgeBase()
        if kb.initialize():
            results = kb.search_documents(collection, query, limit)
            print(json.dumps(results))
        else:
            print(json.dumps({"error": "Failed to initialize knowledge base"}))
    except Exception as e:
        print(json.dumps({"error": f"Search failed: {str(e)}"}))

asyncio.run(search_knowledge())
`;
      const tempScript = path.join(os.tmpdir(), "search_" + Date.now() + "_" + Math.random().toString(36).substr(2, 9) + ".py");
      try {
        fs.writeFileSync(tempScript, searchScript);
      } catch (error) {
        console.error("Failed to write temporary script:", error);
        return res.status(500).json({
          error: "Failed to create search script",
          details: error.message
        });
      }
      const pythonProcess = spawn("python3", [tempScript], {
        cwd: "/Volumes/NHB_Workspace/awakened_mind",
        env: {
          ...process.env,
          PYTHONPATH: "/Volumes/NHB_Workspace/awakened_mind",
          SEARCH_COLLECTION: sanitizedCollection,
          SEARCH_QUERY: sanitizedQuery,
          SEARCH_LIMIT: safeLimit.toString()
        }
      });
      let stdout = "";
      let stderr = "";
      let hasResponse = false;
      const timeout = setTimeout(() => {
        if (!hasResponse) {
          hasResponse = true;
          pythonProcess.kill("SIGTERM");
          try {
            fs.unlinkSync(tempScript);
          } catch (e) {
            console.error("Failed to cleanup temp file:", e);
          }
          res.status(500).json({
            error: "Search operation timed out",
            details: "The search operation took too long to complete"
          });
        }
      }, 3e4);
      pythonProcess.stdout.on("data", (data) => {
        stdout += data.toString();
      });
      pythonProcess.stderr.on("data", (data) => {
        stderr += data.toString();
      });
      pythonProcess.on("close", (code) => {
        if (hasResponse) return;
        hasResponse = true;
        clearTimeout(timeout);
        try {
          fs.unlinkSync(tempScript);
        } catch (e) {
          console.error("Failed to cleanup temp file:", e);
        }
        if (!pythonProcess.killed) {
          pythonProcess.kill("SIGTERM");
        }
      });
      pythonProcess.on("error", (error) => {
        if (hasResponse) return;
        hasResponse = true;
        clearTimeout(timeout);
        try {
          fs.unlinkSync(tempScript);
        } catch (e) {
          console.error("Failed to cleanup temp file after process error:", e);
        }
        console.error("Python process error:", error);
        res.status(500).json({
          error: "Search process failed",
          details: error.message
        });
      });
    } catch (error) {
      res.status(500).json({
        error: "Search request failed",
        details: error.message
      });
    }
  });
  app2.get("/api/collections", async (req, res) => {
    try {
      const pythonScript = `
import json
from core.chroma_connection import NHBKnowledgeBase

kb = NHBKnowledgeBase()
if kb.initialize():
    collections = kb.list_collections()
    stats = kb.get_collection_stats()
    result = []
    for collection in collections:
        result.append({
            'name': collection,
            'count': stats.get(collection, {}).get('count', 0)
        })
    print(json.dumps(result))
else:
    print(json.dumps([]))
`;
      const tempScript = path.join(os.tmpdir(), "collections_" + Date.now() + "_" + Math.random().toString(36).substr(2, 9) + ".py");
      try {
        fs.writeFileSync(tempScript, pythonScript);
      } catch (error) {
        console.error("Failed to write collections script:", error);
        return res.status(500).json({
          error: "Failed to create collections script",
          details: error.message
        });
      }
      const pythonProcess = spawn("python3", [tempScript], {
        cwd: "/Volumes/NHB_Workspace/awakened_mind",
        env: {
          ...process.env,
          PYTHONPATH: "/Volumes/NHB_Workspace/awakened_mind"
        }
      });
      let stdout = "";
      let stderr = "";
      let hasResponse = false;
      const timeout = setTimeout(() => {
        if (!hasResponse) {
          hasResponse = true;
          pythonProcess.kill("SIGTERM");
          try {
            fs.unlinkSync(tempScript);
          } catch (e) {
            console.error("Failed to cleanup temp file:", e);
          }
          res.status(500).json({
            error: "Collections operation timed out",
            details: "The collections operation took too long to complete"
          });
        }
      }, 15e3);
      pythonProcess.stdout.on("data", (data) => {
        stdout += data.toString();
      });
      pythonProcess.stderr.on("data", (data) => {
        stderr += data.toString();
      });
      pythonProcess.on("close", (code) => {
        if (hasResponse) return;
        hasResponse = true;
        clearTimeout(timeout);
        try {
          fs.unlinkSync(tempScript);
        } catch (e) {
          console.error("Failed to cleanup temp file:", e);
        }
        if (code === 0) {
          try {
            const collections = JSON.parse(stdout);
            res.json({ collections });
          } catch (parseError) {
            res.status(500).json({
              error: "Failed to parse collections data",
              details: parseError.message
            });
          }
        } else {
          res.status(500).json({
            error: "Failed to get collections",
            details: stderr
          });
        }
      });
    } catch (error) {
      res.status(500).json({
        error: "Collections request failed",
        details: error.message
      });
    }
  });
  app2.post("/api/knowledge/harvest", async (req, res) => {
    try {
      const pythonScript = `
import asyncio
import json
import sys
from core.mcp_orchestrator import MCPKnowledgeOrchestrator

async def run_harvest():
    orchestrator = MCPKnowledgeOrchestrator()
    if await orchestrator.initialize_components():
        result = await orchestrator.process_pipeline()
        print(json.dumps(result))
    else:
        print(json.dumps({"status": "error", "error": "Failed to initialize components"}))

asyncio.run(run_harvest())
`;
      const tempScript = path.join(os.tmpdir(), "harvest_" + Date.now() + "_" + Math.random().toString(36).substr(2, 9) + ".py");
      try {
        fs.writeFileSync(tempScript, pythonScript);
      } catch (error) {
        console.error("Failed to write harvest script:", error);
        return res.status(500).json({
          error: "Failed to create harvest script",
          details: error.message
        });
      }
      const pythonProcess = spawn("python3", [tempScript], {
        cwd: "/Volumes/NHB_Workspace/awakened_mind",
        env: {
          ...process.env,
          PYTHONPATH: "/Volumes/NHB_Workspace/awakened_mind"
        }
      });
      let stdout = "";
      let stderr = "";
      let hasResponse = false;
      const timeout = setTimeout(() => {
        if (!hasResponse) {
          hasResponse = true;
          pythonProcess.kill("SIGTERM");
          try {
            fs.unlinkSync(tempScript);
          } catch (e) {
            console.error("Failed to cleanup temp file:", e);
          }
          res.status(500).json({
            error: "Harvest operation timed out",
            details: "The harvest operation took too long to complete (5+ minutes)"
          });
        }
      }, 3e5);
      pythonProcess.stdout.on("data", (data) => {
        stdout += data.toString();
      });
      pythonProcess.stderr.on("data", (data) => {
        stderr += data.toString();
      });
      pythonProcess.on("close", (code) => {
        if (hasResponse) return;
        hasResponse = true;
        clearTimeout(timeout);
        try {
          fs.unlinkSync(tempScript);
        } catch (e) {
          console.error("Failed to cleanup temp file:", e);
        }
        if (code === 0) {
          try {
            const result = JSON.parse(stdout);
            res.json(result);
          } catch (parseError) {
            res.status(500).json({
              error: "Failed to parse harvest results",
              details: parseError.message
            });
          }
        } else {
          res.status(500).json({
            error: "Knowledge harvest failed",
            details: stderr
          });
        }
      });
    } catch (error) {
      res.status(500).json({
        error: "Harvest request failed",
        details: error.message
      });
    }
  });
  return app2;
}
if (import.meta.url === `file://${process.argv[1]}`) {
  const app2 = createServer();
  {
    app2.use(express__default.static(path.join(__dirname$1, "../dist")));
  }
  app2.listen(PORT, () => {
    console.log(`🚀 Awakened Mind GUI API server running on port ${PORT}`);
    console.log(`📊 Health check: http://localhost:${PORT}/api/health`);
    console.log(`🔍 Knowledge search: http://localhost:${PORT}/api/knowledge/search`);
    console.log(`📚 Collections: http://localhost:${PORT}/api/collections`);
  });
}
const app = createServer();
const port = process.env.PORT || 3e3;
const __dirname = import.meta.dirname;
const distPath = path.join(__dirname, "../spa");
app.use(express.static(distPath));
app.get("*", (req, res) => {
  if (req.path.startsWith("/api/") || req.path.startsWith("/health")) {
    return res.status(404).json({ error: "API endpoint not found" });
  }
  res.sendFile(path.join(distPath, "index.html"));
});
app.listen(port, () => {
  console.log(`🚀 Fusion Starter server running on port ${port}`);
  console.log(`📱 Frontend: http://localhost:${port}`);
  console.log(`🔧 API: http://localhost:${port}/api`);
});
process.on("SIGTERM", () => {
  console.log("🛑 Received SIGTERM, shutting down gracefully");
  process.exit(0);
});
process.on("SIGINT", () => {
  console.log("🛑 Received SIGINT, shutting down gracefully");
  process.exit(0);
});
//# sourceMappingURL=node-build.mjs.map
