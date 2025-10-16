import express from 'express';
import cors from 'cors';

const app = express();
const PORT = 3002;

// Middleware
app.use(cors());
app.use(express.json());

// Simple test endpoint
app.get('/test', (req, res) => {
    res.json({
        status: 'ok',
        message: 'Test server is working!',
        timestamp: new Date().toISOString()
    });
});

// Health check endpoint
app.get('/api/health', (req, res) => {
    res.json({
        status: 'healthy',
        timestamp: new Date().toISOString(),
        service: 'Test API Server'
    });
});

app.listen(PORT, () => {
    console.log(`🧪 Test server running on port ${PORT}`);
    console.log(`📊 Health check: http://localhost:${PORT}/api/health`);
    console.log(`🧪 Test endpoint: http://localhost:${PORT}/test`);
});
