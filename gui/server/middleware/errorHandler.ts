import { Request, Response, NextFunction } from 'express';
import { z } from 'zod';

/**
 * Custom error classes for better error handling
 */
export class AppError extends Error {
  public statusCode: number;
  public isOperational: boolean;
  public errorCode?: string;

  constructor(message: string, statusCode: number = 500, errorCode?: string) {
    super(message);
    this.statusCode = statusCode;
    this.isOperational = true;
    this.errorCode = errorCode;

    Error.captureStackTrace(this, this.constructor);
  }
}

export class ValidationError extends AppError {
  constructor(message: string, details?: any) {
    super(message, 400, 'VALIDATION_ERROR');
    this.details = details;
  }
  public details?: any;
}

export class AuthenticationError extends AppError {
  constructor(message: string = 'Authentication failed') {
    super(message, 401, 'AUTHENTICATION_ERROR');
  }
}

export class AuthorizationError extends AppError {
  constructor(message: string = 'Insufficient permissions') {
    super(message, 403, 'AUTHORIZATION_ERROR');
  }
}

export class NotFoundError extends AppError {
  constructor(resource: string = 'Resource') {
    super(`${resource} not found`, 404, 'NOT_FOUND');
  }
}

export class RateLimitError extends AppError {
  constructor(message: string = 'Rate limit exceeded') {
    super(message, 429, 'RATE_LIMIT_EXCEEDED');
  }
}

export class ExternalServiceError extends AppError {
  constructor(service: string, originalError?: Error) {
    super(`External service error: ${service}`, 502, 'EXTERNAL_SERVICE_ERROR');
    this.originalError = originalError;
  }
  public originalError?: Error;
}

/**
 * Centralized error handling middleware
 */
export const errorHandler = (
  err: Error,
  req: Request,
  res: Response,
  next: NextFunction
): void => {
  let error: any = { ...err };
  error.message = err.message;

  // Log error for debugging (only in development or for operational errors)
  if (process.env.NODE_ENV === 'development' || (err as any).isOperational !== false) {
    console.error('Error occurred:', {
      message: err.message,
      stack: err.stack,
      url: req.originalUrl,
      method: req.method,
      ip: req.ip,
      userAgent: req.get('User-Agent'),
      timestamp: new Date().toISOString()
    });
  }

  // Handle different error types
  if (err instanceof z.ZodError) {
    const validationError = new ValidationError('Validation failed', {
      errors: err.errors.map(error => ({
        field: error.path.join('.'),
        message: error.message,
        code: error.code
      }))
    });
    error = validationError;
  }

  if (err.name === 'ValidationError') {
    const message = 'Invalid data provided';
    error = new ValidationError(message);
  }

  if (err.name === 'CastError') {
    const message = 'Invalid resource identifier';
    error = new NotFoundError(message);
  }

  if (err.name === 'MongoError' && (err as any).code === 11000) {
    const message = 'Duplicate entry';
    error = new ValidationError(message);
  }

  if (err.name === 'JsonWebTokenError') {
    const message = 'Invalid authentication token';
    error = new AuthenticationError(message);
  }

  if (err.name === 'TokenExpiredError') {
    const message = 'Authentication token expired';
    error = new AuthenticationError(message);
  }

  if (err.name === 'MulterError') {
    const message = 'File upload error';
    error = new ValidationError(message);
  }

  // Handle custom AppError instances
  if (err instanceof AppError) {
    error = err;
  }

  // Mongoose bad ObjectId
  if (err.name === 'CastError') {
    const message = 'Resource not found';
    error = new NotFoundError(message);
  }

  // Mongoose duplicate key
  if (err.name === 'MongoError' && (err as any).code === 11000) {
    const message = 'Duplicate field value entered';
    error = new ValidationError(message);
  }

  // Mongoose validation error
  if (err.name === 'ValidationError') {
    const message = Object.values((err as any).errors).map((val: any) => val.message).join(', ');
    error = new ValidationError(message);
  }

  // Default server error
  if (!error.statusCode || error.statusCode === 200) {
    error.statusCode = 500;
  }

  // Prepare error response
  const errorResponse: any = {
    success: false,
    error: error.message || 'Server Error',
    timestamp: new Date().toISOString()
  };

  // Add error code if available
  if ((error as any).errorCode) {
    errorResponse.code = (error as any).errorCode;
  }

  // Add validation details if available
  if ((error as any).details) {
    errorResponse.details = (error as any).details;
  }

  // Add stack trace only in development
  if (process.env.NODE_ENV === 'development') {
    errorResponse.stack = err.stack;
    errorResponse.originalError = err.message;
  }

  // Handle specific status codes
  switch (error.statusCode) {
    case 400:
      errorResponse.error = errorResponse.error || 'Bad Request';
      break;
    case 401:
      errorResponse.error = errorResponse.error || 'Unauthorized';
      break;
    case 403:
      errorResponse.error = errorResponse.error || 'Forbidden';
      break;
    case 404:
      errorResponse.error = errorResponse.error || 'Not Found';
      break;
    case 429:
      errorResponse.error = errorResponse.error || 'Too Many Requests';
      break;
    case 500:
      errorResponse.error = errorResponse.error || 'Internal Server Error';
      break;
    default:
      errorResponse.error = errorResponse.error || 'Server Error';
  }

  // Send error response
  res.status(error.statusCode).json(errorResponse);
};

/**
 * Async error wrapper for route handlers
 */
export const asyncHandler = (fn: Function) => {
  return (req: Request, res: Response, next: NextFunction) => {
    Promise.resolve(fn(req, res, next)).catch(next);
  };
};

/**
 * 404 handler for unmatched routes
 */
export const notFoundHandler = (req: Request, res: Response, next: NextFunction): void => {
  const error = new NotFoundError(`Route ${req.originalUrl} not found`);
  next(error);
};

/**
 * Request logging middleware for debugging
 */
export const requestLogger = (req: Request, res: Response, next: NextFunction): void => {
  const start = Date.now();

  // Log request
  if (process.env.NODE_ENV === 'development') {
    console.log(`${new Date().toISOString()} - ${req.method} ${req.originalUrl}`);
  }

  // Override res.end to log response
  const originalEnd = res.end;
  res.end = function(chunk?: any, encoding?: BufferEncoding | (() => void)) {
    const duration = Date.now() - start;

    if (process.env.NODE_ENV === 'development') {
      console.log(`${new Date().toISOString()} - ${req.method} ${req.originalUrl} - ${res.statusCode} - ${duration}ms`);
    }

    // Call original end method
    return originalEnd.call(this, chunk, encoding);
  };

  next();
};

/**
 * Security headers middleware
 */
export const securityHeaders = (req: Request, res: Response, next: NextFunction): void => {
  // Basic security headers
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-Frame-Options', 'DENY');
  res.setHeader('X-XSS-Protection', '1; mode=block');
  res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');

  // Remove server information
  res.removeHeader('X-Powered-By');

  next();
};

/**
 * CORS configuration
 */
export const corsOptions = {
  origin: (origin: any, callback: any) => {
    // Allow requests with no origin (mobile apps, etc.)
    if (!origin) return callback(null, true);

    const allowedOrigins = process.env.ALLOWED_ORIGINS?.split(',') || [
      'http://localhost:3000',
      'http://localhost:5173',
      'http://localhost:4173'
    ];

    if (allowedOrigins.includes(origin)) {
      return callback(null, true);
    }

    callback(new Error('Not allowed by CORS'));
  },
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With']
};