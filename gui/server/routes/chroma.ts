/**
 * Awakened Mind Knowledge Base API Routes
 * Connects the GUI to the ChromaDB system via core/chroma_connection.py
 */

import { RequestHandler } from "express";
import { exec } from "child_process";
import { promisify } from "util";
import fs from "fs/promises";
import path from "path";

const execAsync = promisify(exec);

// Path to the awakened mind workspace
const WORKSPACE_ROOT = "/Volumes/NHB_Workspace/awakened_mind";

// Define API response types
export interface KnowledgeSearchResponse {
  success: boolean;
  results: Array<{
    collection: string;
    documents: string[];
    metadatas: any[];
    distances: number[];
  }>;
  error?: string;
}

export interface CollectionStatusResponse {
  success: boolean;
  collections: Array<{
    name: string;
    description: string;
    documentCount?: number;
  }>;
}

export interface SystemHealthResponse {
  success: boolean;
  status: {
    knowledge: boolean;
    memories: boolean;
    activeMind: boolean;
    archive: boolean;
    littleBrain: boolean;
  };
  vitality: any;
  totalKnowledgeCount?: number;
}

export interface AddKnowledgeRequest {
  content: string;
  metadata: {
    source: string;
    type: string;
    collection?: string;
    tags?: string[];
  };
  agent?: string;
}

// Get system health status using our new connection layer
export const handleSystemHealth: RequestHandler = async (req, res) => {
  try {
    // Run Python script to get comprehensive system status
    const pythonScript = `
import sys
sys.path.append('${WORKSPACE_ROOT}')
sys.path.append('${WORKSPACE_ROOT}/core')
sys.path.append('${WORKSPACE_ROOT}/configs')
from configs.path_manager import get_path_manager
from chroma_connection import get_knowledge_base
import json
import os

# Get path manager
pm = get_path_manager()

# Check volume accessibility
volumes = pm._check_volume_accessibility()

# Get ChromaDB status and knowledge count
try:
    kb = get_knowledge_base()
    total_count = kb.get_total_knowledge_count()
    chroma_status = True
except Exception as e:
    total_count = 0
    chroma_status = False

# Read vitality report if exists
vitality = None
try:
    vitality_path = pm.get_volume_path('active_mind') / 'signals' / 'system_vitality.json'
    if vitality_path.exists():
        with open(vitality_path, 'r') as f:
            vitality = json.load(f)
except:
    pass

# Prepare output
output = {
    "success": True,
    "status": volumes,
    "vitality": vitality,
    "totalKnowledgeCount": total_count,
    "chromaStatus": chroma_status
}

print(json.dumps(output))
`;

    // Escape single quotes in the Python script for shell execution
    const escapedScript = pythonScript.replace(/'/g, "'\"'\"'");
    const { stdout, stderr } = await execAsync(`cd ${WORKSPACE_ROOT} && python3 -c '${escapedScript}'`);
    
    if (stderr && !stderr.includes("Warning")) {
      throw new Error(`Python script error: ${stderr}`);
    }

    const systemData = JSON.parse(stdout);
    res.json(systemData);
    
  } catch (error) {
    console.error('System health check failed:', error);
    res.status(500).json({
      success: false,
      error: error.message,
      status: { knowledge: false, memories: false, activeMind: false, archive: false, littleBrain: false },
      vitality: null,
      totalKnowledgeCount: 0
    });
  }
};

// Get collection status using our new connection layer
export const handleCollectionStatus: RequestHandler = async (req, res) => {
  try {
    const pythonScript = `
import sys
sys.path.append('${WORKSPACE_ROOT}/core')
sys.path.append('${WORKSPACE_ROOT}/configs')
from chroma_connection import get_knowledge_base
import json

# Get knowledge base and collection stats
kb = get_knowledge_base()
stats = kb.get_collection_stats()
collection_names = kb.list_collections()

# Map collection names to descriptions
descriptions = {
    "github_projects": "GitHub repositories and code patterns",
    "technical_docs": "Technical documentation and guides",
    "nhb_interactions": "NHB collaborative knowledge",
    "current_events": "Time-sensitive information",
    "code_patterns": "Reusable code templates and solutions",
    "collective_wisdom": "Synthesized collective intelligence",
    "realtime_cache": "Fast-access session data",
    "session_memory": "User session persistence"
}

collections = []
for name in collection_names:
    collections.append({
        "name": name,
        "description": descriptions.get(name, "Knowledge collection"),
        "documentCount": stats.get(name, {}).get("count", 0)
    })

output = {
    "success": True,
    "collections": collections
}

print(json.dumps(output))
`;

    // Escape single quotes in the Python script for shell execution
    const escapedScript = pythonScript.replace(/'/g, "'\"'\"'");
    const { stdout, stderr } = await execAsync(`cd ${WORKSPACE_ROOT} && python3 -c '${escapedScript}'`);
    
    if (stderr && !stderr.includes("Warning")) {
      throw new Error(`Python script error: ${stderr}`);
    }

    const collectionsData = JSON.parse(stdout);
    res.json(collectionsData);
    
  } catch (error) {
    console.error('Collection status check failed:', error);
    res.status(500).json({
      success: false,
      error: error.message,
      collections: []
    });
  }
};

// Search knowledge base using our new connection layer
export const handleKnowledgeSearch: RequestHandler = async (req, res) => {
  try {
    const { query, collection, limit = 5 } = req.body;
    
    if (!query) {
      return res.status(400).json({
        success: false,
        error: "Query parameter is required"
      });
    }

    // Escape quotes in query for Python script
    const escapedQuery = query.replace(/"/g, '\\"').replace(/'/g, "\\'");
    const targetCollection = collection || 'technical_docs';
    
    const pythonScript = `
import sys
sys.path.append('${WORKSPACE_ROOT}/core')
sys.path.append('${WORKSPACE_ROOT}/configs')
from chroma_connection import get_knowledge_base
import json

# Get knowledge base
kb = get_knowledge_base()

# Search in the specified collection
results = kb.search_documents('${targetCollection}', '${escapedQuery}', ${limit})

# Format results for frontend
formatted_results = {
    '${targetCollection}': {
        'documents': [r.get('document', '') for r in results],
        'metadatas': [r.get('metadata', {}) for r in results],
        'distances': [r.get('distance', 0) for r in results]
    }
}

print(json.dumps(formatted_results))
`;

    // Escape single quotes in the Python script for shell execution
    const escapedScript = pythonScript.replace(/'/g, "'\"'\"'");
    const { stdout, stderr } = await execAsync(`cd ${WORKSPACE_ROOT} && python3 -c '${escapedScript}'`);
    
    if (stderr && !stderr.includes("Warning")) {
      throw new Error(`Search failed: ${stderr}`);
    }

    const searchResults = JSON.parse(stdout);
    
    const response: KnowledgeSearchResponse = {
      success: true,
      results: Object.entries(searchResults).map(([collectionName, data]: [string, any]) => ({
        collection: collectionName,
        documents: data.documents || [],
        metadatas: data.metadatas || [],
        distances: data.distances || []
      }))
    };

    res.json(response);
    
  } catch (error) {
    console.error('Knowledge search failed:', error);
    res.status(500).json({
      success: false,
      error: error.message,
      results: []
    });
  }
};

// Add knowledge to the system using our new connection layer
export const handleAddKnowledge: RequestHandler = async (req, res) => {
  try {
    const { content, metadata, agent = "gui_user" }: AddKnowledgeRequest = req.body;
    
    if (!content || !metadata) {
      return res.status(400).json({
        success: false,
        error: "Content and metadata are required"
      });
    }

    // Escape content for Python script
    const escapedContent = content.replace(/"/g, '\\"').replace(/'/g, "\\'");
    const targetCollection = metadata.collection || 'collective_wisdom';
    
    const pythonScript = `
import sys
sys.path.append('${WORKSPACE_ROOT}/core')
sys.path.append('${WORKSPACE_ROOT}/configs')
from chroma_connection import get_knowledge_base
import json
import time

# Get knowledge base
kb = get_knowledge_base()

# Prepare document for our ChromaDB connection layer
doc_id = f'gui_{int(time.time())}_{agent}'
document = {
    'id': doc_id,
    'content': '${escapedContent}',
    'source': '${metadata.source}',
    'type': '${metadata.type}',
    'agent': '${agent}',
    'timestamp': time.time()
}

# Add additional metadata fields if provided
metadata_dict = ${JSON.stringify(metadata)}
for key, value in metadata_dict.items():
    if key not in ['collection']:
        document[key] = value

# Add to the specified collection
success = kb.add_documents('${targetCollection}', [document])

if not success:
    raise Exception("Failed to add document to ChromaDB")
    
print(doc_id)
`;

    // Escape single quotes in the Python script for shell execution
    const escapedScript = pythonScript.replace(/'/g, "'\"'\"'");
    const { stdout, stderr } = await execAsync(`cd ${WORKSPACE_ROOT} && python3 -c '${escapedScript}'`);
    
    if (stderr && !stderr.includes("Warning")) {
      throw new Error(`Add knowledge failed: ${stderr}`);
    }

    res.json({
      success: true,
      documentId: stdout.trim(),
      message: "Knowledge added successfully to the Awakened Mind"
    });
    
  } catch (error) {
    console.error('Add knowledge failed:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
};

// Get GitHub scraper status
export const handleScraperStatus: RequestHandler = async (req, res) => {
  try {
    const signalPath = "/Volumes/Active_Mind/signals/last_discovery.json";
    let lastDiscovery = null;
    
    try {
      const data = await fs.readFile(signalPath, "utf-8");
      lastDiscovery = JSON.parse(data);
    } catch (e) {
      // No discovery yet
    }

    // Check if scraper is running
    const { stdout } = await execAsync("ps aux | grep universal_github_integration | grep -v grep");
    const isRunning = stdout.length > 0;

    res.json({
      success: true,
      isRunning,
      lastDiscovery,
      message: isRunning ? "GitHub scraper is actively discovering knowledge" : "GitHub scraper is not running"
    });
  } catch (error) {
    res.json({
      success: true,
      isRunning: false,
      lastDiscovery: null,
      message: "GitHub scraper status unknown"
    });
  }
};

// Start GitHub scraper
export const handleStartScraper: RequestHandler = async (req, res) => {
  try {
    const command = "cd /Volumes/Active_Mind/scrapers && nohup python3 universal_github_integration.py > /Volumes/Active_Mind/logs/github_discovery.log 2>&1 &";
    await execAsync(command);
    
    res.json({
      success: true,
      message: "GitHub scraper started successfully"
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
};
