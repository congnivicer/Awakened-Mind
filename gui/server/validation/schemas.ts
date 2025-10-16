import { z } from 'zod';

/**
 * Comprehensive validation schemas for all API endpoints
 */

// Base schemas for common data types
export const uuidSchema = z.string().uuid('Invalid UUID format');

export const emailSchema = z.string()
  .email('Invalid email format')
  .max(254, 'Email too long');

export const urlSchema = z.string()
  .url('Invalid URL format')
  .max(2048, 'URL too long');

export const timestampSchema = z.string()
  .datetime('Invalid timestamp format');

// Search endpoint validation
export const searchSchema = z.object({
  query: z.string()
    .min(1, 'Search query cannot be empty')
    .max(500, 'Search query too long')
    .regex(/^[a-zA-Z0-9\s\-_.,!?()]+$/, 'Query contains invalid characters')
    .transform((val) => val.trim()),

  limit: z.number()
    .int('Limit must be a whole number')
    .min(1, 'Limit must be at least 1')
    .max(100, 'Limit cannot exceed 100')
    .default(10),

  collection: z.string()
    .max(100, 'Collection name too long')
    .regex(/^[a-zA-Z0-9_-]+$/, 'Invalid collection name format')
    .optional(),

  filters: z.object({
    documentType: z.enum(['github_repository', 'code_documentation', 'api_documentation', 'technical_documentation'])
      .optional(),
    minScore: z.number().min(0).max(1).optional(),
    dateFrom: timestampSchema.optional(),
    dateTo: timestampSchema.optional()
  }).optional()
});

// Add document endpoint validation
export const addDocumentSchema = z.object({
  content: z.string()
    .min(10, 'Document content too short (minimum 10 characters)')
    .max(50000, 'Document content too long (maximum 50,000 characters)')
    .refine((val) => {
      // Check for potentially dangerous content
      const dangerousPatterns = [
        /<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi,
        /javascript:/gi,
        /vbscript:/gi,
        /onload\s*=/gi,
        /onerror\s*=/gi,
        /onclick\s*=/gi,
        /<iframe\b/gi,
        /<object\b/gi,
        /<embed\b/gi
      ];

      return !dangerousPatterns.some(pattern => pattern.test(val));
    }, 'Content contains potentially dangerous patterns'),

  metadata: z.object({
    source: urlSchema,
    collection: z.string()
      .min(1, 'Collection name is required')
      .max(100, 'Collection name too long')
      .regex(/^[a-zA-Z0-9_-]+$/, 'Invalid collection name format'),
    type: z.enum(['github_repository', 'code_documentation', 'api_documentation', 'technical_documentation', 'manual'])
      .default('manual'),
    title: z.string()
      .max(200, 'Title too long')
      .optional(),
    description: z.string()
      .max(1000, 'Description too long')
      .optional(),
    tags: z.array(z.string()
      .min(1, 'Tag cannot be empty')
      .max(50, 'Tag too long')
      .regex(/^[a-zA-Z0-9_-]+$/, 'Invalid tag format'))
      .max(20, 'Too many tags')
      .optional(),
    language: z.string()
      .max(50, 'Language identifier too long')
      .optional()
  }).strict(),

  agent: z.string()
    .min(1, 'Agent identifier required')
    .max(100, 'Agent identifier too long')
    .default('gui_user')
});

// Health check endpoint validation
export const healthCheckSchema = z.object({
  includeDetails: z.boolean().default(false),
  checkExternal: z.boolean().default(false)
}).optional();

// Collection management validation
export const collectionSchema = z.object({
  name: z.string()
    .min(1, 'Collection name cannot be empty')
    .max(100, 'Collection name too long')
    .regex(/^[a-zA-Z0-9_-]+$/, 'Collection name contains invalid characters'),

  description: z.string()
    .max(500, 'Description too long')
    .optional(),

  metadata: z.record(z.any()).optional()
});

// Batch operations validation
export const batchOperationSchema = z.object({
  operation: z.enum(['add', 'update', 'delete']),
  documents: z.array(addDocumentSchema.omit({ agent: true }))
    .min(1, 'At least one document required')
    .max(50, 'Too many documents in batch (maximum 50)'),

  collection: z.string()
    .min(1, 'Collection name required')
    .max(100, 'Collection name too long'),

  agent: z.string()
    .min(1, 'Agent identifier required')
    .max(100, 'Agent identifier too long')
    .default('gui_user')
});

// Analytics and metrics validation
export const metricsSchema = z.object({
  timeRange: z.object({
    start: timestampSchema,
    end: timestampSchema
  }),
  granularity: z.enum(['hour', 'day', 'week', 'month']).default('day'),
  collections: z.array(z.string()).max(20, 'Too many collections').optional()
});

// User authentication validation
export const loginSchema = z.object({
  email: emailSchema,
  password: z.string()
    .min(8, 'Password must be at least 8 characters')
    .max(128, 'Password too long')
});

// User registration validation
export const registerSchema = z.object({
  email: emailSchema,
  password: z.string()
    .min(8, 'Password must be at least 8 characters')
    .max(128, 'Password too long')
    .regex(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/, 'Password must contain at least one lowercase letter, one uppercase letter, and one number'),
  role: z.enum(['user', 'moderator', 'admin']).default('user')
});

// Pagination validation
export const paginationSchema = z.object({
  page: z.number()
    .int('Page must be a whole number')
    .min(1, 'Page must be at least 1')
    .default(1),

  limit: z.number()
    .int('Limit must be a whole number')
    .min(1, 'Limit must be at least 1')
    .max(100, 'Limit cannot exceed 100')
    .default(20),

  sortBy: z.string()
    .max(50, 'Sort field too long')
    .optional(),

  sortOrder: z.enum(['asc', 'desc']).default('desc')
});

// Export type inference helpers
export type SearchRequest = z.infer<typeof searchSchema>;
export type AddDocumentRequest = z.infer<typeof addDocumentSchema>;
export type HealthCheckRequest = z.infer<typeof healthCheckSchema>;
export type CollectionRequest = z.infer<typeof collectionSchema>;
export type BatchOperationRequest = z.infer<typeof batchOperationSchema>;
export type MetricsRequest = z.infer<typeof metricsSchema>;
export type LoginRequest = z.infer<typeof loginSchema>;
export type RegisterRequest = z.infer<typeof registerSchema>;
export type PaginationRequest = z.infer<typeof paginationSchema>;

// Validation middleware helper
export class ValidationMiddleware {
  /**
   * Validate request body against schema
   */
  static validateBody = <T extends z.ZodSchema>(schema: T) => {
    return (req: any, res: any, next: any) => {
      try {
        const validatedData = schema.parse(req.body);
        req.body = validatedData; // Replace with validated data
        next();
      } catch (error: any) {
        if (error instanceof z.ZodError) {
          res.status(400).json({
            success: false,
            error: 'Validation failed',
            code: 'VALIDATION_ERROR',
            details: error.errors.map(err => ({
              field: err.path.join('.'),
              message: err.message,
              code: err.code
            }))
          });
          return;
        }
        next(error);
      }
    };
  };

  /**
   * Validate request query parameters against schema
   */
  static validateQuery = <T extends z.ZodSchema>(schema: T) => {
    return (req: any, res: any, next: any) => {
      try {
        const validatedData = schema.parse(req.query);
        req.query = validatedData; // Replace with validated data
        next();
      } catch (error: any) {
        if (error instanceof z.ZodError) {
          res.status(400).json({
            success: false,
            error: 'Query validation failed',
            code: 'QUERY_VALIDATION_ERROR',
            details: error.errors.map(err => ({
              field: err.path.join('.'),
              message: err.message,
              code: err.code
            }))
          });
          return;
        }
        next(error);
      }
    };
  };

  /**
   * Validate request parameters against schema
   */
  static validateParams = <T extends z.ZodSchema>(schema: T) => {
    return (req: any, res: any, next: any) => {
      try {
        const validatedData = schema.parse(req.params);
        req.params = validatedData; // Replace with validated data
        next();
      } catch (error: any) {
        if (error instanceof z.ZodError) {
          res.status(400).json({
            success: false,
            error: 'Parameter validation failed',
            code: 'PARAM_VALIDATION_ERROR',
            details: error.errors.map(err => ({
              field: err.path.join('.'),
              message: err.message,
              code: err.code
            }))
          });
          return;
        }
        next(error);
      }
    };
  };
}