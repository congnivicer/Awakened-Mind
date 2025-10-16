import express from 'express';
import cors from 'cors';

const app = express();
const PORT = 3001;

// Middleware
app.use(cors());
app.use(express.json());

// Mock endpoints for GUI to load
app.get('/api/chroma/health', (req, res) => {
  res.json({
    success: true,
    status: {
      knowledge: true,
      memories: true,
      activeMind: true,
      archive: true
    }
  });
});

app.get('/api/chroma/collections', (req, res) => {
  res.json({
    success: true,
    collections: [
      { name: 'github_projects', count: 0, description: 'GitHub Projects' },
      { name: 'technical_docs', count: 16, description: 'Technical Documentation' },
      { name: 'nhb_interactions', count: 0, description: 'NHB Interactions' },
      { name: 'current_events', count: 0, description: 'Current Events' },
      { name: 'code_patterns', count: 0, description: 'Code Patterns' },
      { name: 'collective_wisdom', count: 0, description: 'Collective Wisdom' }
    ]
  });
});

app.post('/api/chroma/search', (req, res) => {
  res.json({
    success: true,
    results: []
  });
});

app.post('/api/chroma/add', (req, res) => {
  res.json({
    success: true,
    message: 'Content added successfully'
  });
});

app.listen(PORT, () => {
  console.log(`🚀 Simple API Server running on port ${PORT}`);
  console.log(`📡 Endpoints: http://localhost:${PORT}/api/chroma/*`);
});
