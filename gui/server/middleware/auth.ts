import jwt from 'jsonwebtoken';
import { Request, Response, NextFunction } from 'express';

// Extend Express Request interface to include user
export interface AuthUser {
  id: string;
  email: string;
  role: string;
  iat?: number;
  exp?: number;
}

export interface AuthRequest extends Request {
  user?: AuthUser;
}

/**
 * Authentication middleware using JWT tokens
 */
export class AuthMiddleware {
  private jwtSecret: string | undefined;
  private jwtExpiresIn: string;

  constructor() {
    this.jwtSecret = process.env.JWT_SECRET;
    this.jwtExpiresIn = process.env.JWT_EXPIRES_IN || '24h';

    if (!this.jwtSecret) {
      throw new Error(
        'JWT_SECRET environment variable is required for security. ' +
        'Please set it to a secure random string (minimum 32 characters). ' +
        'Generate with: node -e "console.log(require(\'crypto\').randomBytes(64).toString(\'hex\'))"'
      );
    }

    console.log('[AUTH_MIDDLEWARE] JWT configuration validated successfully');
  }

  /**
   * Middleware to authenticate JWT tokens
   */
  authenticateToken = async (req: AuthRequest, res: Response, next: NextFunction): Promise<void> => {
    try {
      const authHeader = req.headers['authorization'];
      const token = authHeader && authHeader.split(' ')[1]; // Bearer TOKEN

      if (!token) {
        console.log('[AUTH_DEBUG] No token provided in request');
        res.status(401).json({
          success: false,
          error: 'Access token required',
          code: 'AUTH_TOKEN_MISSING'
        });
        return;
      }

      // Verify token
      console.log('[AUTH_DEBUG] Verifying token:', { hasToken: !!token, secretConfigured: !!this.jwtSecret });

      interface JwtPayload {
        id?: string;
        userId?: string;
        email: string;
        role?: string;
        iat?: number;
        exp?: number;
      }

      const decoded = jwt.verify(token, this.jwtSecret) as JwtPayload;
      console.log('[AUTH_DEBUG] Token decoded successfully:', { userId: decoded.id || decoded.userId, role: decoded.role });

      // Validate required fields
      if (!decoded.email) {
        throw new Error('Token missing required email field');
      }

      // Add user info to request object
      req.user = {
        id: decoded.id || decoded.userId || '',
        email: decoded.email,
        role: decoded.role || 'user',
        iat: decoded.iat,
        exp: decoded.exp
      };

      next();
    } catch (error: any) {
      if (error.name === 'TokenExpiredError') {
        res.status(401).json({
          success: false,
          error: 'Token has expired',
          code: 'AUTH_TOKEN_EXPIRED'
        });
        return;
      }

      if (error.name === 'JsonWebTokenError') {
        res.status(403).json({
          success: false,
          error: 'Invalid token',
          code: 'AUTH_TOKEN_INVALID'
        });
        return;
      }

      console.error('Authentication error:', error);
      res.status(500).json({
        success: false,
        error: 'Authentication failed',
        code: 'AUTH_INTERNAL_ERROR'
      });
    }
  };

  /**
   * Middleware to check for specific roles
   */
  requireRole = (roles: string | string[]) => {
    return (req: AuthRequest, res: Response, next: NextFunction): void => {
      if (!req.user) {
        res.status(401).json({
          success: false,
          error: 'Authentication required',
          code: 'AUTH_REQUIRED'
        });
        return;
      }

      const allowedRoles = Array.isArray(roles) ? roles : [roles];
      const userRole = req.user.role || 'user';

      if (!allowedRoles.includes(userRole)) {
        res.status(403).json({
          success: false,
          error: 'Insufficient permissions',
          code: 'AUTH_INSUFFICIENT_PERMISSIONS',
          required: allowedRoles,
          current: userRole
        });
        return;
      }

      next();
    };
  };

  /**
   * Middleware to check for admin role
   */
  requireAdmin = this.requireRole('admin');

  /**
   * Middleware to check for moderator or admin role
   */
  requireModerator = this.requireRole(['moderator', 'admin']);

  /**
   * Optional authentication - adds user info if token present but doesn't require it
   */
  optionalAuth = async (req: AuthRequest, res: Response, next: NextFunction): Promise<void> => {
    try {
      const authHeader = req.headers['authorization'];
      const token = authHeader && authHeader.split(' ')[1];

      if (token) {
        interface JwtPayload {
          id?: string;
          userId?: string;
          email: string;
          role?: string;
          iat?: number;
          exp?: number;
        }

        try {
          const decoded = jwt.verify(token, this.jwtSecret) as JwtPayload;

          if (!decoded.email) {
            console.log('[AUTH_DEBUG] Token missing email field in optional auth');
            return next();
          }

          req.user = {
            id: decoded.id || decoded.userId || '',
            email: decoded.email,
            role: decoded.role || 'user',
            iat: decoded.iat,
            exp: decoded.exp
          };
        } catch (error) {
          console.log('[AUTH_DEBUG] Token verification failed in optional auth:', error.message);
          // Continue without user for optional auth
        }
      }

      next();
    } catch (error) {
      // For optional auth, we ignore token errors and continue
      next();
    }
  };

  /**
   * Generate JWT token for user
   */
  generateToken(payload: { id: string; email: string; role?: string }): string {
    const tokenPayload = {
      id: payload.id,
      email: payload.email,
      role: payload.role || 'user'
    };

    if (!this.jwtSecret) {
      throw new Error('JWT secret not configured');
    }

    return jwt.sign(tokenPayload, this.jwtSecret as jwt.Secret, {
      expiresIn: this.jwtExpiresIn,
      issuer: 'nhb-knowledge-infrastructure',
      audience: 'nhb-api-users'
    } as jwt.SignOptions);
  }

  /**
   * Verify token without middleware (for internal use)
   */
  verifyToken(token: string): AuthUser | null {
    try {
      interface JwtPayload {
        id?: string;
        userId?: string;
        email: string;
        role?: string;
        iat?: number;
        exp?: number;
      }

      const decoded = jwt.verify(token, this.jwtSecret) as JwtPayload;

      if (!decoded.email) {
        return null;
      }

      return {
        id: decoded.id || decoded.userId || '',
        email: decoded.email,
        role: decoded.role || 'user',
        iat: decoded.iat,
        exp: decoded.exp
      };
    } catch (error) {
      console.log('[AUTH_DEBUG] Token verification failed in verifyToken:', error.message);
      return null;
    }
  }
}

// Export singleton instance
export const authMiddleware = new AuthMiddleware();