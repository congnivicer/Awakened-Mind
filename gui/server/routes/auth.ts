import express from 'express';
import { authController } from '../controllers/authController';
import { authMiddleware } from '../middleware/auth';
import { authLimiter } from '../middleware/rateLimit';
import { ValidationMiddleware } from '../validation/schemas';

const router = express.Router();

/**
 * Authentication routes with comprehensive security
 */

// Apply rate limiting to all auth routes
router.use(authLimiter);

/**
 * POST /api/auth/login
 * Authenticate user with email and password
 */
router.post('/login',
  ValidationMiddleware.validateBody({
    email: 'string',
    password: 'string'
  } as any),
  authController.login
);

/**
 * POST /api/auth/register
 * Register new user account
 */
router.post('/register',
  ValidationMiddleware.validateBody({
    email: 'string',
    password: 'string',
    role: 'string'
  } as any),
  authController.register
);

/**
 * POST /api/auth/logout
 * Logout user (client-side token removal)
 */
router.post('/logout',
  authController.logout
);

/**
 * POST /api/auth/refresh
 * Refresh JWT token
 */
router.post('/refresh',
  ValidationMiddleware.validateBody({
    token: 'string'
  } as any),
  authController.refreshToken
);

/**
 * POST /api/auth/change-password
 * Change user password (requires authentication)
 */
router.post('/change-password',
  authMiddleware.authenticateToken,
  ValidationMiddleware.validateBody({
    currentPassword: 'string',
    newPassword: 'string'
  } as any),
  authController.changePassword
);

/**
 * GET /api/auth/me
 * Get current user information (requires authentication)
 */
router.get('/me',
  authMiddleware.authenticateToken,
  authController.getCurrentUser
);

/**
 * GET /api/auth/permissions
 * Get current user permissions (requires authentication)
 */
router.get('/permissions',
  authMiddleware.authenticateToken,
  authController.getPermissions
);

/**
 * GET /api/auth/users
 * List all users (requires admin authentication)
 */
router.get('/users',
  authMiddleware.authenticateToken,
  authMiddleware.requireRole('admin'),
  authController.listUsers
);

/**
 * PUT /api/auth/users/:userId
 * Update user information (requires admin authentication)
 */
router.put('/users/:userId',
  authMiddleware.authenticateToken,
  authMiddleware.requireRole('admin'),
  ValidationMiddleware.validateParams({
    userId: 'string'
  } as any),
  ValidationMiddleware.validateBody({
    role: 'string',
    isActive: 'boolean'
  } as any),
  authController.updateUser
);

/**
 * DELETE /api/auth/users/:userId
 * Delete/deactivate user (requires admin authentication)
 */
router.delete('/users/:userId',
  authMiddleware.authenticateToken,
  authMiddleware.requireRole('admin'),
  ValidationMiddleware.validateParams({
    userId: 'string'
  } as any),
  authController.deleteUser
);

export default router;