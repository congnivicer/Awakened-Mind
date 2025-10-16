import rateLimit from 'express-rate-limit';
import { Request, Response } from 'express';

/**
 * Rate limiting middleware configurations
 */

// General API rate limiting
export const generalLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: (req: Request) => {
    // More permissive for authenticated users
    if ((req as any).user) {
      return 200; // 200 requests per 15 minutes for authenticated users
    }
    return 100; // 100 requests per 15 minutes for anonymous users
  },
  message: {
    success: false,
    error: 'Too many requests from this IP, please try again later.',
    code: 'RATE_LIMIT_EXCEEDED',
    retryAfter: Math.ceil(15 * 60 / 100) // Suggest retry time in seconds
  },
  standardHeaders: true, // Return rate limit info in `RateLimit-*` headers
  legacyHeaders: false, // Disable the `X-RateLimit-*` headers
  // Skip rate limiting for health checks
  skip: (req: Request) => {
    return req.path === '/health' || req.path.startsWith('/health');
  },
  // Custom key generator to differentiate by user
  keyGenerator: (req: Request) => {
    const user = (req as any).user;
    if (user && user.id) {
      return `user_${user.id}`;
    }
    return req.ip || req.connection.remoteAddress || 'unknown';
  }
});

// Strict rate limiting for sensitive operations
export const strictLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: (req: Request) => {
    if ((req as any).user) {
      return 20; // 20 requests per 15 minutes for authenticated users
    }
    return 5; // 5 requests per 15 minutes for anonymous users
  },
  message: {
    success: false,
    error: 'Too many requests for this operation, please try again later.',
    code: 'STRICT_RATE_LIMIT_EXCEEDED',
    retryAfter: Math.ceil(15 * 60 / 20)
  },
  standardHeaders: true,
  legacyHeaders: false,
  keyGenerator: (req: Request) => {
    const user = (req as any).user;
    if (user && user.id) {
      return `strict_user_${user.id}`;
    }
    return `strict_${req.ip || req.connection.remoteAddress || 'unknown'}`;
  }
});

// Search-specific rate limiting (more permissive as it's read-only)
export const searchLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: (req: Request) => {
    if ((req as any).user) {
      return 500; // 500 search requests per 15 minutes for authenticated users
    }
    return 200; // 200 search requests per 15 minutes for anonymous users
  },
  message: {
    success: false,
    error: 'Too many search requests, please try again later.',
    code: 'SEARCH_RATE_LIMIT_EXCEEDED',
    retryAfter: Math.ceil(15 * 60 / 200)
  },
  standardHeaders: true,
  legacyHeaders: false,
  keyGenerator: (req: Request) => {
    const user = (req as any).user;
    if (user && user.id) {
      return `search_user_${user.id}`;
    }
    return `search_${req.ip || req.connection.remoteAddress || 'unknown'}`;
  }
});

// Authentication rate limiting (very strict for login attempts)
export const authLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 5, // 5 login attempts per 15 minutes per IP
  message: {
    success: false,
    error: 'Too many authentication attempts, please try again later.',
    code: 'AUTH_RATE_LIMIT_EXCEEDED',
    retryAfter: Math.ceil(15 * 60 / 5)
  },
  standardHeaders: true,
  legacyHeaders: false,
  skipSuccessfulRequests: true, // Don't count successful logins against the limit
  keyGenerator: (req: Request) => {
    return `auth_${req.ip || req.connection.remoteAddress || 'unknown'}`;
  }
});

// Document creation rate limiting
export const creationLimiter = rateLimit({
  windowMs: 60 * 1000, // 1 minute
  max: (req: Request) => {
    if ((req as any).user) {
      return 10; // 10 documents per minute for authenticated users
    }
    return 2; // 2 documents per minute for anonymous users
  },
  message: {
    success: false,
    error: 'Too many document creation requests, please slow down.',
    code: 'CREATION_RATE_LIMIT_EXCEEDED',
    retryAfter: Math.ceil(60 / 10)
  },
  standardHeaders: true,
  legacyHeaders: false,
  keyGenerator: (req: Request) => {
    const user = (req as any).user;
    if (user && user.id) {
      return `create_user_${user.id}`;
    }
    return `create_${req.ip || req.connection.remoteAddress || 'unknown'}`;
  }
});

/**
 * Dynamic rate limiter based on user role and operation type
 */
export class DynamicRateLimiter {
  private limits: Map<string, { count: number; resetTime: number; lastAccess: number }> = new Map();
  private readonly maxEntries: number = 10000; // Prevent memory leaks

  constructor(private windowMs: number = 60000) {} // 1 minute default

  middleware(maxRequests: number, identifier?: string) {
    return (req: Request, res: Response, next: any) => {
      const key = identifier || this.generateKey(req);
      const now = Date.now();
      const windowStart = now - this.windowMs;

      // DEBUG: Log memory usage and cleanup operations
      console.log(`[RATE_LIMIT_DEBUG] Dynamic limiter check for key: ${key}, Map size: ${this.limits.size}`);

      // Clean up old entries and enforce size limits
      const beforeCleanup = this.limits.size;
      this.cleanup(windowStart);

      // Additional memory management: remove oldest entries if we're approaching the limit
      if (this.limits.size >= this.maxEntries) {
        this.evictOldEntries();
      }

      const afterCleanup = this.limits.size;
      if (beforeCleanup !== afterCleanup) {
        console.log(`[RATE_LIMIT_DEBUG] Cleaned up ${beforeCleanup - afterCleanup} old entries`);
      }

      // Get or create limit entry
      let entry = this.limits.get(key);
      if (!entry || entry.resetTime < windowStart) {
        entry = { count: 0, resetTime: now + this.windowMs, lastAccess: now };
        this.limits.set(key, entry);
      }

      // Update last access time
      entry.lastAccess = now;

      // Check if limit exceeded (atomic check)
      if (entry.count >= maxRequests) {
        const retryAfter = Math.ceil((entry.resetTime - now) / 1000);
        console.log(`[RATE_LIMIT_DEBUG] Rate limit exceeded for key: ${key}, count: ${entry.count}, limit: ${maxRequests}`);
        res.status(429).json({
          success: false,
          error: 'Rate limit exceeded',
          code: 'DYNAMIC_RATE_LIMIT_EXCEEDED',
          retryAfter
        });
        return;
      }

      // Increment counter atomically
      entry.count++;
      console.log(`[RATE_LIMIT_DEBUG] Rate limit check passed for key: ${key}, count: ${entry.count}/${maxRequests}`);

      // Add rate limit headers
      res.set({
        'X-RateLimit-Limit': maxRequests,
        'X-RateLimit-Remaining': Math.max(0, maxRequests - entry.count),
        'X-RateLimit-Reset': entry.resetTime
      });

      next();
    };
  }

  private generateKey(req: Request): string {
    const user = (req as any).user;
    if (user && user.id) {
      return `dynamic_user_${user.id}`;
    }
    return `dynamic_${req.ip || req.connection.remoteAddress || 'unknown'}`;
  }

  private cleanup(beforeTime: number): void {
    for (const [key, entry] of this.limits.entries()) {
      if (entry.resetTime < beforeTime) {
        this.limits.delete(key);
      }
    }
  }

  private evictOldEntries(): void {
    // Sort entries by last access time (oldest first)
    const entries = Array.from(this.limits.entries()).sort((a, b) => a[1].lastAccess - b[1].lastAccess);

    // Remove oldest 20% of entries
    const toRemove = Math.floor(this.maxEntries * 0.2);
    for (let i = 0; i < toRemove && i < entries.length; i++) {
      this.limits.delete(entries[i][0]);
    }

    console.log(`[RATE_LIMIT_DEBUG] Evicted ${toRemove} old entries, Map size: ${this.limits.size}`);
  }
}

// Export dynamic limiter instance
export const dynamicLimiter = new DynamicRateLimiter();

/**
 * Rate limiting configuration by endpoint
 */
export const rateLimitConfig = {
  // Public endpoints (no auth required)
  '/api/health': { limiter: null, skip: true }, // No rate limiting for health checks
  '/api/search': { limiter: searchLimiter },

  // Authentication endpoints
  '/api/auth/login': { limiter: authLimiter },
  '/api/auth/register': { limiter: authLimiter },

  // Protected endpoints (require auth)
  '/api/collections': { limiter: generalLimiter },
  '/api/chroma/collections': { limiter: generalLimiter },
  '/api/chroma/search': { limiter: searchLimiter },
  '/api/chroma/add': { limiter: creationLimiter },
  '/api/chroma/health': { limiter: generalLimiter },

  // Admin endpoints (require admin role)
  '/api/admin/*': { limiter: strictLimiter },

  // Default for unmatched routes
  'default': { limiter: generalLimiter }
};

/**
 * Get rate limiter for specific route
 */
export function getRateLimiter(route: string): any {
  // Check for exact match
  if (rateLimitConfig[route]) {
    return rateLimitConfig[route].limiter;
  }

  // Check for pattern match (admin routes)
  for (const [pattern, config] of Object.entries(rateLimitConfig)) {
    if (pattern.includes('*') && route.startsWith(pattern.replace('*', ''))) {
      return config.limiter;
    }
  }

  // Return default
  return rateLimitConfig.default.limiter;
}