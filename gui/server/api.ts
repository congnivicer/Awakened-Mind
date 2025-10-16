import express, { Request, Response } from 'express';
import path from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

// Import security middleware and services
import { authMiddleware, AuthRequest } from './middleware/auth';
import { ValidationMiddleware } from './validation/schemas';
import { generalLimiter, searchLimiter, creationLimiter } from './middleware/rateLimit';
import { asyncHandler, notFoundHandler, errorHandler, securityHeaders } from './middleware/errorHandler';
import {
  resourceTrackingMiddleware,
  gracefulShutdownMiddleware,
  memoryMonitoringMiddleware,
  connectionPoolMiddleware
} from './middleware/resourceCleanup';

// Import secure Python execution service
import { pythonExecutor } from './services/pythonExecutor';

// Import authentication routes
import authRoutes from './routes/auth';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const router = express.Router();

// Apply security and resource management middleware to all routes
router.use(securityHeaders);
router.use(memoryMonitoringMiddleware);
router.use(resourceTrackingMiddleware);
router.use(connectionPoolMiddleware);
router.use(generalLimiter);

// Mount authentication routes
router.use('/auth', authRoutes);

/**
 * SECURE API ROUTES - All critical security vulnerabilities fixed
 */

/**
 * GET /api/chroma/health
 * Check system health and volume status (SECURED)
 */
router.get('/health',
  asyncHandler(async (req: Request, res: Response) => {
    // Use secure Python execution service
    const result = await pythonExecutor.executePythonFunction({
      scriptName: 'chroma_connection.py',
      functionName: 'get_knowledge_base_health',
      parameters: {
        includeDetails: req.query.includeDetails === 'true',
        checkExternal: req.query.checkExternal === 'true'
      }
    });

    if (!result.success) {
      throw new Error(result.error || 'Health check failed');
    }

    res.json({
      success: true,
      status: result.data,
      timestamp: new Date().toISOString()
    });
  })
);

/**
 * GET /api/chroma/collections
 * List all ChromaDB collections with stats (SECURED)
 */
router.get('/collections',
  ValidationMiddleware.validateQuery({
    includeStats: { type: 'boolean', default: true },
    collectionFilter: { type: 'string', optional: true }
  } as any),
  asyncHandler(async (req: Request, res: Response) => {
    const result = await pythonExecutor.executePythonFunction({
      scriptName: 'chroma_connection.py',
      functionName: 'get_collections_with_stats',
      parameters: {
        includeStats: req.query.includeStats,
        collectionFilter: req.query.collectionFilter
      }
    });

    if (!result.success) {
      throw new Error(result.error || 'Failed to retrieve collections');
    }

    res.json({
      success: true,
      collections: result.data,
      timestamp: new Date().toISOString()
    });
  })
);

/**
 * POST /api/chroma/search
 * Search across all collections (SECURED)
 */
router.post('/search',
  searchLimiter,
  ValidationMiddleware.validateBody({
    query: 'string',
    limit: 'number',
    collection: 'string',
    filters: 'object'
  } as any),
  asyncHandler(async (req: Request, res: Response) => {
    const result = await pythonExecutor.executePythonFunction({
      scriptName: 'chroma_connection.py',
      functionName: 'search_across_collections',
      parameters: {
        query: req.body.query,
        limit: req.body.limit || 10,
        collection: req.body.collection,
        filters: req.body.filters || {}
      }
    });

    if (!result.success) {
      throw new Error(result.error || 'Search failed');
    }

    res.json({
      success: true,
      results: result.data,
      timestamp: new Date().toISOString(),
      query: req.body.query
    });
  })
);

/**
 * POST /api/chroma/add
 * Add new knowledge to a collection (SECURED)
 */
router.post('/add',
  authMiddleware.authenticateToken, // Require authentication
  creationLimiter,
  ValidationMiddleware.validateBody({
    content: 'string',
    metadata: 'object',
    agent: 'string'
  } as any),
  asyncHandler(async (req: AuthRequest, res: Response) => {
    // Get user info from authenticated token
    const userId = req.user?.id || 'anonymous';
    const userEmail = req.user?.email || 'anonymous@local';

    const result = await pythonExecutor.executePythonFunction({
      scriptName: 'chroma_connection.py',
      functionName: 'add_document_secure',
      parameters: {
        content: req.body.content,
        metadata: req.body.metadata,
        agent: req.body.agent,
        userId: userId,
        userEmail: userEmail
      }
    });

    if (!result.success) {
      throw new Error(result.error || 'Failed to add document');
    }

    res.status(201).json({
      success: true,
      documentId: result.data.documentId,
      collection: result.data.collection,
      timestamp: new Date().toISOString(),
      addedBy: userEmail
    });
  })
);

export default router;
