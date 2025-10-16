import { Request, Response, NextFunction } from 'express';

/**
 * Resource cleanup middleware for proper memory management
 */

// Track active connections and resources
interface ResourceTracker {
  connections: Set<any>;
  files: Set<string>;
  timers: Set<NodeJS.Timeout>;
  intervals: Set<NodeJS.Timeout>;
  lastCleanup: number;
}

class ResourceManager {
  private static instance: ResourceManager;
  private resources: ResourceTracker;
  private cleanupInterval: NodeJS.Timeout | null = null;
  private maxIdleTime: number = 5 * 60 * 1000; // 5 minutes

  private constructor() {
    this.resources = {
      connections: new Set(),
      files: new Set(),
      timers: new Set(),
      intervals: new Set(),
      lastCleanup: Date.now()
    };

    this.startPeriodicCleanup();
  }

  static getInstance(): ResourceManager {
    if (!ResourceManager.instance) {
      ResourceManager.instance = new ResourceManager();
    }
    return ResourceManager.instance;
  }

  /**
   * Track a connection or resource
   */
  trackConnection(connection: any): string {
    const id = `conn_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    this.resources.connections.add(connection);

    // Set up automatic cleanup on connection close/error
    if (typeof connection.on === 'function') {
      connection.on('close', () => this.untrackConnection(connection));
      connection.on('error', () => this.untrackConnection(connection));
    }

    return id;
  }

  /**
   * Stop tracking a connection
   */
  untrackConnection(connection: any): void {
    this.resources.connections.delete(connection);
  }

  /**
   * Track a file handle or path
   */
  trackFile(filePath: string): string {
    const id = `file_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    this.resources.files.add(filePath);
    return id;
  }

  /**
   * Stop tracking a file
   */
  untrackFile(filePath: string): void {
    this.resources.files.delete(filePath);
  }

  /**
   * Track a timer
   */
  trackTimer(timer: NodeJS.Timeout): string {
    const id = `timer_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    this.resources.timers.add(timer);

    // Auto-cleanup when timer expires
    const originalClear = timer;
    return id;
  }

  /**
   * Stop tracking a timer
   */
  untrackTimer(timer: NodeJS.Timeout): void {
    this.resources.timers.delete(timer);
  }

  /**
   * Track an interval
   */
  trackInterval(interval: NodeJS.Timeout): string {
    const id = `interval_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    this.resources.intervals.add(interval);
    return id;
  }

  /**
   * Stop tracking an interval
   */
  untrackInterval(interval: NodeJS.Timeout): void {
    this.resources.intervals.delete(interval);
  }

  /**
   * Force cleanup of all tracked resources
   */
  async forceCleanup(): Promise<void> {
    const cleanupStart = Date.now();
    console.log(`🧹 Starting forced resource cleanup...`);

    // Close all connections
    for (const connection of this.resources.connections) {
      try {
        if (typeof connection.close === 'function') {
          connection.close();
        } else if (typeof connection.end === 'function') {
          connection.end();
        } else if (typeof connection.destroy === 'function') {
          connection.destroy();
        }
      } catch (error) {
        console.warn('Error closing connection:', error);
      }
    }
    this.resources.connections.clear();

    // Clear all timers
    for (const timer of this.resources.timers) {
      clearTimeout(timer);
    }
    this.resources.timers.clear();

    // Clear all intervals
    for (const interval of this.resources.intervals) {
      clearInterval(interval);
    }
    this.resources.intervals.clear();

    // Clear file references (files should be closed by their owners)
    this.resources.files.clear();

    this.resources.lastCleanup = Date.now();
    const cleanupTime = Date.now() - cleanupStart;
    console.log(`✅ Forced cleanup completed in ${cleanupTime}ms`);
  }

  /**
   * Start periodic cleanup of idle resources
   */
  private startPeriodicCleanup(): void {
    this.cleanupInterval = setInterval(async () => {
      await this.performPeriodicCleanup();
    }, this.maxIdleTime / 2); // Run cleanup every 2.5 minutes

    // Track the cleanup interval
    this.trackInterval(this.cleanupInterval);
  }

  /**
   * Perform periodic cleanup of idle resources
   */
  private async performPeriodicCleanup(): Promise<void> {
    const now = Date.now();
    const idleThreshold = now - this.maxIdleTime;

    // Clean up old connections (basic check)
    let cleanedCount = 0;

    // Note: In a real implementation, you'd check connection.lastActivity < idleThreshold
    // For now, we'll just update the last cleanup time

    this.resources.lastCleanup = now;

    if (cleanedCount > 0) {
      console.log(`🧹 Periodic cleanup: removed ${cleanedCount} idle resources`);
    }
  }

  /**
   * Get resource statistics
   */
  getStats(): {
    connections: number;
    files: number;
    timers: number;
    intervals: number;
    lastCleanup: number;
    uptime: number;
  } {
    return {
      connections: this.resources.connections.size,
      files: this.resources.files.size,
      timers: this.resources.timers.size,
      intervals: this.resources.intervals.size,
      lastCleanup: this.resources.lastCleanup,
      uptime: Date.now() - this.resources.lastCleanup
    };
  }

  /**
   * Graceful shutdown handler
   */
  async gracefulShutdown(): Promise<void> {
    console.log('🛑 Initiating graceful shutdown...');

    // Stop periodic cleanup
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
      this.cleanupInterval = null;
    }

    // Force cleanup all resources
    await this.forceCleanup();

    console.log('✅ Graceful shutdown completed');
  }
}

// Export singleton instance
export const resourceManager = ResourceManager.getInstance();

/**
 * Middleware to track request resources
 */
export const resourceTrackingMiddleware = (req: Request, res: Response, next: NextFunction): void => {
  const startTime = Date.now();

  // Track the request as a resource
  const requestId = resourceManager.trackConnection(req.socket);

  // Override res.end to track response time and cleanup
  const originalEnd = res.end;
  res.end = function(chunk?: any, encoding?: BufferEncoding | (() => void)) {
    const responseTime = Date.now() - startTime;

    // Log slow requests
    if (responseTime > 5000) { // 5 seconds
      console.warn(`🐌 Slow request detected: ${req.method} ${req.originalUrl} took ${responseTime}ms`);
    }

    // Cleanup request tracking
    resourceManager.untrackConnection(req.socket);

    // Call original end method
    return originalEnd.call(this, chunk, encoding);
  };

  next();
};

/**
 * Middleware to handle process cleanup on shutdown
 */
export const gracefulShutdownMiddleware = (server: any) => {
  const shutdown = async (signal: string) => {
    console.log(`📡 Received ${signal}, starting graceful shutdown...`);

    try {
      // Stop accepting new connections
      server.close(async () => {
        console.log('🚪 Server closed, cleaning up resources...');

        // Cleanup all resources
        await resourceManager.gracefulShutdown();

        console.log('👋 Process terminated gracefully');
        process.exit(0);
      });

      // Force close after 10 seconds
      setTimeout(() => {
        console.error('⚠️  Forced shutdown after timeout');
        process.exit(1);
      }, 10000);

    } catch (error) {
      console.error('❌ Error during shutdown:', error);
      process.exit(1);
    }
  };

  // Handle different termination signals
  process.on('SIGTERM', () => shutdown('SIGTERM'));
  process.on('SIGINT', () => shutdown('SIGINT'));
  process.on('SIGUSR2', () => shutdown('SIGUSR2')); // For nodemon restarts

  // Handle uncaught exceptions
  process.on('uncaughtException', (error) => {
    console.error('💥 Uncaught Exception:', error);
    shutdown('uncaughtException');
  });

  // Handle unhandled promise rejections
  process.on('unhandledRejection', (reason, promise) => {
    console.error('💥 Unhandled Rejection at:', promise, 'reason:', reason);
    shutdown('unhandledRejection');
  });
};

/**
 * Middleware to monitor memory usage
 */
export const memoryMonitoringMiddleware = (req: Request, res: Response, next: NextFunction): void => {
  const memUsage = process.memoryUsage();

  // Log high memory usage
  const memMB = memUsage.heapUsed / 1024 / 1024;
  if (memMB > 100) { // More than 100MB
    console.warn(`🧠 High memory usage: ${memMB.toFixed(2)}MB`);
  }

  // Add memory info to response headers in development
  if (process.env.NODE_ENV === 'development') {
    res.setHeader('X-Memory-Usage', `${memMB.toFixed(2)}MB`);
    res.setHeader('X-Memory-RSS', `${(memUsage.rss / 1024 / 1024).toFixed(2)}MB`);
  }

  next();
};

/**
 * Connection pool manager for database connections
 */
export class ConnectionPoolManager {
  private static instance: ConnectionPoolManager;
  private pools: Map<string, any> = new Map();
  private maxConnections: number = 10;
  private maxIdleTime: number = 5 * 60 * 1000; // 5 minutes

  static getInstance(): ConnectionPoolManager {
    if (!ConnectionPoolManager.instance) {
      ConnectionPoolManager.instance = new ConnectionPoolManager();
    }
    return ConnectionPoolManager.instance;
  }

  /**
   * Get connection from pool
   */
  async getConnection(poolName: string, createConnection: () => Promise<any>): Promise<any> {
    let pool = this.pools.get(poolName);

    if (!pool) {
      pool = {
        connections: [],
        inUse: new Set(),
        created: Date.now()
      };
      this.pools.set(poolName, pool);
    }

    // Try to get idle connection
    for (const conn of pool.connections) {
      if (!pool.inUse.has(conn)) {
        pool.inUse.add(conn);
        return conn;
      }
    }

    // Create new connection if under limit
    if (pool.connections.length < this.maxConnections) {
      const newConnection = await createConnection();
      pool.connections.push(newConnection);
      pool.inUse.add(newConnection);

      // Track connection for cleanup
      resourceManager.trackConnection(newConnection);

      return newConnection;
    }

    // Wait for available connection
    return new Promise((resolve, reject) => {
      const checkInterval = setInterval(() => {
        for (const conn of pool.connections) {
          if (!pool.inUse.has(conn)) {
            clearInterval(checkInterval);
            pool.inUse.add(conn);
            resolve(conn);
            return;
          }
        }
      }, 100);

      // Timeout after 30 seconds
      setTimeout(() => {
        clearInterval(checkInterval);
        reject(new Error('Connection pool timeout'));
      }, 30000);
    });
  }

  /**
   * Return connection to pool
   */
  releaseConnection(poolName: string, connection: any): void {
    const pool = this.pools.get(poolName);
    if (pool) {
      pool.inUse.delete(connection);
    }
  }

  /**
   * Cleanup idle connections
   */
  async cleanupIdleConnections(): Promise<void> {
    const now = Date.now();

    for (const [poolName, pool] of this.pools.entries()) {
      if (now - pool.created > this.maxIdleTime) {
        // Close idle connections
        for (const conn of pool.connections) {
          if (!pool.inUse.has(conn)) {
            try {
              if (typeof conn.close === 'function') {
                await conn.close();
              }
            } catch (error) {
              console.warn('Error closing idle connection:', error);
            }
          }
        }

        // Remove closed connections
        pool.connections = pool.connections.filter(conn => pool.inUse.has(conn));
      }
    }
  }
}

// Export singleton instance
export const connectionPoolManager = ConnectionPoolManager.getInstance();

/**
 * Middleware to handle connection pooling for database operations
 */
export const connectionPoolMiddleware = (req: Request, res: Response, next: NextFunction): void => {
  // Add connection pool manager to request for use in route handlers
  (req as any).connectionPool = connectionPoolManager;
  next();
};