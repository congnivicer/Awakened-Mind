import { Request, Response } from 'express';
import { AuthRequest } from '../middleware/auth';
import { authService, User, UserRole, Permission } from '../services/authService';
import { asyncHandler } from '../middleware/errorHandler';

/**
 * Authentication controller handling all auth-related endpoints
 */
export class AuthController {

  /**
   * POST /api/auth/login
   * Authenticate user and return JWT token
   */
  login = asyncHandler(async (req: Request, res: Response) => {
    const { email, password } = req.body;

    if (!email || !password) {
      res.status(400).json({
        success: false,
        error: 'Email and password are required',
        code: 'MISSING_CREDENTIALS'
      });
      return;
    }

    // Authenticate user
    const authResult = await authService.authenticateUser(email, password);

    if (!authResult) {
      res.status(401).json({
        success: false,
        error: 'Invalid email or password',
        code: 'INVALID_CREDENTIALS'
      });
      return;
    }

    const { user, token } = authResult;

    // Return user info and token
    res.json({
      success: true,
      message: 'Login successful',
      data: {
        user: {
          id: user.id,
          email: user.email,
          role: user.role,
          lastLogin: user.lastLogin,
          createdAt: user.createdAt
        },
        token,
        permissions: authService.getRolePermissions(user.role),
        expiresIn: process.env.JWT_EXPIRES_IN || '24h'
      }
    });
  });

  /**
   * POST /api/auth/register
   * Register new user account
   */
  register = asyncHandler(async (req: Request, res: Response) => {
    const { email, password, role = UserRole.USER } = req.body;

    if (!email || !password) {
      res.status(400).json({
        success: false,
        error: 'Email and password are required',
        code: 'MISSING_CREDENTIALS'
      });
      return;
    }

    // Validate password strength
    if (password.length < 8) {
      res.status(400).json({
        success: false,
        error: 'Password must be at least 8 characters long',
        code: 'WEAK_PASSWORD'
      });
      return;
    }

    try {
      // Register user
      const user = await authService.registerUser(email, password, role);

      // Generate token for immediate login
      const token = authService.generateToken(user);

      res.status(201).json({
        success: true,
        message: 'Registration successful',
        data: {
          user: {
            id: user.id,
            email: user.email,
            role: user.role,
            createdAt: user.createdAt
          },
          token,
          permissions: authService.getRolePermissions(user.role),
          expiresIn: process.env.JWT_EXPIRES_IN || '24h'
        }
      });
    } catch (error: any) {
      res.status(409).json({
        success: false,
        error: error.message,
        code: 'REGISTRATION_FAILED'
      });
    }
  });

  /**
   * POST /api/auth/logout
   * Logout user (client-side token removal)
   */
  logout = asyncHandler(async (req: Request, res: Response) => {
    // For stateless JWT, logout is handled client-side
    // This endpoint can be used for cleanup or audit logging

    res.json({
      success: true,
      message: 'Logout successful',
      data: {
        timestamp: new Date().toISOString()
      }
    });
  });

  /**
   * GET /api/auth/me
   * Get current user information
   */
  getCurrentUser = asyncHandler(async (req: AuthRequest, res: Response) => {
    const user = req.user;

    if (!user) {
      res.status(401).json({
        success: false,
        error: 'Not authenticated',
        code: 'NOT_AUTHENTICATED'
      });
      return;
    }

    // Get full user data
    const userData = authService.getUserById(user.id);

    if (!userData) {
      res.status(404).json({
        success: false,
        error: 'User not found',
        code: 'USER_NOT_FOUND'
      });
      return;
    }

    res.json({
      success: true,
      data: {
        user: {
          id: userData.id,
          email: userData.email,
          role: userData.role,
          isActive: userData.isActive,
          lastLogin: userData.lastLogin,
          createdAt: userData.createdAt,
          updatedAt: userData.updatedAt
        },
        permissions: authService.getRolePermissions(userData.role)
      }
    });
  });

  /**
   * POST /api/auth/refresh
   * Refresh JWT token
   */
  refreshToken = asyncHandler(async (req: Request, res: Response) => {
    const { token } = req.body;

    if (!token) {
      res.status(400).json({
        success: false,
        error: 'Refresh token is required',
        code: 'MISSING_REFRESH_TOKEN'
      });
      return;
    }

    try {
      const newToken = authService.refreshToken(token);

      if (!newToken) {
        res.status(401).json({
          success: false,
          error: 'Invalid or expired refresh token',
          code: 'INVALID_REFRESH_TOKEN'
        });
        return;
      }

      // Verify new token to get user info
      const tokenData = authService.verifyToken(newToken);

      res.json({
        success: true,
        message: 'Token refreshed successfully',
        data: {
          token: newToken,
          expiresIn: process.env.JWT_EXPIRES_IN || '24h'
        }
      });
    } catch (error: any) {
      res.status(401).json({
        success: false,
        error: 'Token refresh failed',
        code: 'TOKEN_REFRESH_FAILED'
      });
    }
  });

  /**
   * POST /api/auth/change-password
   * Change user password
   */
  changePassword = asyncHandler(async (req: AuthRequest, res: Response) => {
    const { currentPassword, newPassword } = req.body;
    const userId = req.user?.id;

    if (!userId) {
      res.status(401).json({
        success: false,
        error: 'Not authenticated',
        code: 'NOT_AUTHENTICATED'
      });
      return;
    }

    if (!currentPassword || !newPassword) {
      res.status(400).json({
        success: false,
        error: 'Current password and new password are required',
        code: 'MISSING_PASSWORDS'
      });
      return;
    }

    if (newPassword.length < 8) {
      res.status(400).json({
        success: false,
        error: 'New password must be at least 8 characters long',
        code: 'WEAK_NEW_PASSWORD'
      });
      return;
    }

    try {
      const success = await authService.changePassword(userId, currentPassword, newPassword);

      if (!success) {
        res.status(400).json({
          success: false,
          error: 'Current password is incorrect',
          code: 'INVALID_CURRENT_PASSWORD'
        });
        return;
      }

      res.json({
        success: true,
        message: 'Password changed successfully'
      });
    } catch (error: any) {
      res.status(500).json({
        success: false,
        error: 'Failed to change password',
        code: 'PASSWORD_CHANGE_FAILED'
      });
    }
  });

  /**
   * GET /api/auth/permissions
   * Get current user permissions
   */
  getPermissions = asyncHandler(async (req: AuthRequest, res: Response) => {
    const user = req.user;

    if (!user) {
      res.status(401).json({
        success: false,
        error: 'Not authenticated',
        code: 'NOT_AUTHENTICATED'
      });
      return;
    }

    const permissions = authService.getRolePermissions(user.role as UserRole);

    res.json({
      success: true,
      data: {
        role: user.role,
        permissions,
        permissionCount: permissions.length
      }
    });
  });

  /**
   * GET /api/auth/users (Admin only)
   * List all users
   */
  listUsers = asyncHandler(async (req: AuthRequest, res: Response) => {
    const currentUser = req.user;

    if (!currentUser) {
      res.status(401).json({
        success: false,
        error: 'Not authenticated',
        code: 'NOT_AUTHENTICATED'
      });
      return;
    }

    // Check if user has admin permissions
    if (!authService.hasPermission(
      { role: currentUser.role as UserRole } as User,
      Permission.MANAGE_USERS
    )) {
      res.status(403).json({
        success: false,
        error: 'Insufficient permissions',
        code: 'INSUFFICIENT_PERMISSIONS'
      });
      return;
    }

    const users = authService.listUsers();
    const stats = authService.getUserStats();

    res.json({
      success: true,
      data: {
        users: users.map(u => ({
          id: u.id,
          email: u.email,
          role: u.role,
          isActive: u.isActive,
          lastLogin: u.lastLogin,
          createdAt: u.createdAt,
          updatedAt: u.updatedAt
        })),
        stats
      }
    });
  });

  /**
   * PUT /api/auth/users/:userId (Admin only)
   * Update user information
   */
  updateUser = asyncHandler(async (req: AuthRequest, res: Response) => {
    const { userId } = req.params;
    const { role, isActive } = req.body;
    const currentUser = req.user;

    if (!currentUser) {
      res.status(401).json({
        success: false,
        error: 'Not authenticated',
        code: 'NOT_AUTHENTICATED'
      });
      return;
    }

    // Check if user has admin permissions
    if (!authService.hasPermission(
      { role: currentUser.role as UserRole } as User,
      Permission.MANAGE_USERS
    )) {
      res.status(403).json({
        success: false,
        error: 'Insufficient permissions',
        code: 'INSUFFICIENT_PERMISSIONS'
      });
      return;
    }

    try {
      const updates: Partial<User> = {};
      if (role) updates.role = role;
      if (typeof isActive === 'boolean') updates.isActive = isActive;

      const updatedUser = await authService.updateUser(userId, updates);

      if (!updatedUser) {
        res.status(404).json({
          success: false,
          error: 'User not found',
          code: 'USER_NOT_FOUND'
        });
        return;
      }

      res.json({
        success: true,
        message: 'User updated successfully',
        data: {
          user: {
            id: updatedUser.id,
            email: updatedUser.email,
            role: updatedUser.role,
            isActive: updatedUser.isActive,
            updatedAt: updatedUser.updatedAt
          }
        }
      });
    } catch (error: any) {
      res.status(400).json({
        success: false,
        error: error.message,
        code: 'USER_UPDATE_FAILED'
      });
    }
  });

  /**
   * DELETE /api/auth/users/:userId (Admin only)
   * Delete/deactivate user
   */
  deleteUser = asyncHandler(async (req: AuthRequest, res: Response) => {
    const { userId } = req.params;
    const currentUser = req.user;

    if (!currentUser) {
      res.status(401).json({
        success: false,
        error: 'Not authenticated',
        code: 'NOT_AUTHENTICATED'
      });
      return;
    }

    // Check if user has admin permissions
    if (!authService.hasPermission(
      { role: currentUser.role as UserRole } as User,
      Permission.MANAGE_USERS
    )) {
      res.status(403).json({
        success: false,
        error: 'Insufficient permissions',
        code: 'INSUFFICIENT_PERMISSIONS'
      });
      return;
    }

    // Prevent self-deletion
    if (userId === currentUser.id) {
      res.status(400).json({
        success: false,
        error: 'Cannot delete your own account',
        code: 'CANNOT_DELETE_SELF'
      });
      return;
    }

    const success = await authService.deleteUser(userId);

    if (!success) {
      res.status(404).json({
        success: false,
        error: 'User not found',
        code: 'USER_NOT_FOUND'
      });
      return;
    }

    res.json({
      success: true,
      message: 'User deleted successfully'
    });
  });
}

// Export controller instance
export const authController = new AuthController();