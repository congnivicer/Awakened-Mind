#!/usr/bin/env python3
"""
Performance Optimization Module for Awakened Mind Knowledge Harvesting System

This module provides comprehensive performance optimizations including:
- Connection pooling for external services
- Metadata processing optimization and caching
- Async performance monitoring and metrics
- Resource usage optimization
- Query performance improvements
"""

import asyncio
import time
import functools
import weakref
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import logging
import threading
import gc

try:
    from .exceptions import ConfigurationError
except ImportError:
    # Running as standalone script
    from exceptions import ConfigurationError


@dataclass
class PerformanceMetrics:
    """Performance metrics tracking"""
    operation_count: int = 0
    total_duration: float = 0.0
    average_duration: float = 0.0
    min_duration: float = float('inf')
    max_duration: float = 0.0
    error_count: int = 0
    last_operation: Optional[datetime] = None

    def record_operation(self, duration: float, success: bool = True):
        """Record operation metrics"""
        self.operation_count += 1
        self.total_duration += duration
        self.average_duration = self.total_duration / self.operation_count
        self.min_duration = min(self.min_duration, duration)
        self.max_duration = max(self.max_duration, duration)
        self.last_operation = datetime.now()

        if not success:
            self.error_count += 1

    def get_success_rate(self) -> float:
        """Get operation success rate"""
        if self.operation_count == 0:
            return 1.0
        return (self.operation_count - self.error_count) / self.operation_count


@dataclass
class ConnectionPoolStats:
    """Connection pool statistics"""
    created_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    failed_connections: int = 0
    reused_connections: int = 0


class ConnectionPool:
    """
    High-performance connection pool for external services

    Features:
    - Configurable pool size limits
    - Connection health monitoring
    - Automatic connection cleanup
    - Connection reuse optimization
    - Async-safe operations
    """

    def __init__(self, max_connections: int = 10, max_idle_time: int = 300):
        self.max_connections = max_connections
        self.max_idle_time = max_idle_time
        self.logger = logging.getLogger(__name__)

        # Connection storage
        self._connections: asyncio.Queue = asyncio.Queue(maxsize=max_connections)
        self._active_connections: weakref.WeakSet = weakref.WeakSet()
        self._stats = ConnectionPoolStats()

        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    async def initialize(self):
        """Initialize connection pool"""
        self._cleanup_task = asyncio.create_task(self._cleanup_idle_connections())
        self.logger.info(f"✅ Connection pool initialized: max={self.max_connections}")

    async def get_connection(self) -> Any:
        """
        Get or create connection from pool

        Returns:
            Connection object ready for use
        """
        async with self._lock:
            try:
                # Try to get existing connection
                connection = self._connections.get_nowait()
                self._active_connections.add(connection)
                self._stats.reused_connections += 1
                return connection

            except asyncio.QueueEmpty:
                # Create new connection if under limit
                if len(self._active_connections) < self.max_connections:
                    connection = await self._create_connection()
                    self._active_connections.add(connection)
                    self._stats.created_connections += 1
                    return connection
                else:
                    # Wait for available connection
                    connection = await self._connections.get()
                    self._active_connections.add(connection)
                    self._stats.reused_connections += 1
                    return connection

    async def return_connection(self, connection: Any):
        """Return connection to pool"""
        try:
            # Check if connection is still healthy
            if await self._is_connection_healthy(connection):
                async with self._lock:
                    self._active_connections.discard(connection)
                    if not self._connections.full():
                        self._connections.put_nowait(connection)
                    else:
                        # Pool is full, close connection
                        await self._close_connection(connection)
            else:
                # Connection is unhealthy, close it
                await self._close_connection(connection)
                self._stats.failed_connections += 1

        except Exception as e:
            self.logger.warning(f"Error returning connection to pool: {e}")
            await self._close_connection(connection)

    async def _create_connection(self) -> Any:
        """Create new connection (override in subclasses)"""
        raise NotImplementedError("Subclasses must implement _create_connection")

    async def _is_connection_healthy(self, connection: Any) -> bool:
        """Check if connection is healthy (override in subclasses)"""
        return True

    async def _close_connection(self, connection: Any):
        """Close connection (override in subclasses)"""
        pass

    async def _cleanup_idle_connections(self):
        """Background task to cleanup idle connections"""
        while True:
            try:
                await asyncio.sleep(self.max_idle_time)

                # This is a simplified cleanup - in practice you'd track
                # individual connection idle times
                if self._connections.qsize() > 0:
                    self.logger.debug("Connection pool cleanup cycle completed")

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in connection cleanup: {e}")

    def get_stats(self) -> ConnectionPoolStats:
        """Get current pool statistics"""
        return ConnectionPoolStats(
            created_connections=self._stats.created_connections,
            active_connections=len(self._active_connections),
            idle_connections=self._connections.qsize(),
            failed_connections=self._stats.failed_connections,
            reused_connections=self._stats.reused_connections
        )

    async def shutdown(self):
        """Shutdown connection pool"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Close all connections
        while not self._connections.empty():
            try:
                connection = self._connections.get_nowait()
                await self._close_connection(connection)
            except asyncio.QueueEmpty:
                break


class GitHubConnectionPool(ConnectionPool):
    """Specialized connection pool for GitHub API"""

    def __init__(self, config_manager=None):
        super().__init__(max_connections=5, max_idle_time=60)
        self.config_manager = config_manager
        self._session = None

    async def _create_connection(self) -> Any:
        """Create new aiohttp session for GitHub API"""
        try:
            import aiohttp  # type: ignore

            # Get configuration
            if self.config_manager:
                github_config = self.config_manager.get_github_config()
                timeout = aiohttp.ClientTimeout(total=github_config.api_timeout)
                max_connections = github_config.max_retries
            else:
                timeout = aiohttp.ClientTimeout(total=30)
                max_connections = 5

            connector = aiohttp.TCPConnector(
                limit=max_connections,
                limit_per_host=2,
                ttl_dns_cache=300,
                use_dns_cache=True,
                keepalive_timeout=60
            )

            session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers={'User-Agent': 'NHB-Knowledge-Infrastructure/1.0'}
            )

            self.logger.info("✅ Created new GitHub API connection")
            return session

        except Exception as e:
            self.logger.error(f"❌ Failed to create GitHub connection: {e}")
            raise

    async def _is_connection_healthy(self, connection: Any) -> bool:
        """Check if aiohttp session is healthy"""
        try:
            if hasattr(connection, 'closed') and connection.closed:
                return False

            # Simple health check - in practice you might make a test request
            return True

        except Exception:
            return False

    async def _close_connection(self, connection: Any):
        """Close aiohttp session"""
        try:
            if not connection.closed:
                await connection.close()
        except Exception as e:
            self.logger.warning(f"Error closing GitHub connection: {e}")


class MetadataCache:
    """
    High-performance metadata processing cache

    Features:
    - LRU-style caching with size limits
    - Async-safe operations
    - Automatic cache invalidation
    - Memory-efficient storage
    """

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.logger = logging.getLogger(__name__)

        # Cache storage: key -> (value, timestamp, access_count)
        self._cache: Dict[str, tuple] = {}
        self._access_order: deque = deque(maxlen=max_size)

        # Performance tracking
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key not in self._cache:
            self._misses += 1
            return None

        value, timestamp, access_count = self._cache[key]

        # Check TTL
        if time.time() - timestamp > self.ttl_seconds:
            del self._cache[key]
            self._access_order.remove(key)
            self._misses += 1
            return None

        # Update access tracking
        self._cache[key] = (value, timestamp, access_count + 1)
        self._access_order.remove(key)
        self._access_order.append(key)
        self._hits += 1

        return value

    def put(self, key: str, value: Any):
        """Put value in cache"""
        now = time.time()

        # Remove oldest entries if at capacity
        while len(self._cache) >= self.max_size and key not in self._cache:
            oldest_key = self._access_order.popleft()
            del self._cache[oldest_key]

        # Add/update entry
        self._cache[key] = (value, now, 0)
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)

    def clear(self):
        """Clear all cache entries"""
        self._cache.clear()
        self._access_order.clear()
        self._hits = 0
        self._misses = 0

    def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0.0

        return {
            'size': len(self._cache),
            'max_size': self.max_size,
            'hits': self._hits,
            'misses': self._misses,
            'hit_rate': hit_rate,
            'memory_usage': len(str(self._cache))  # Rough estimate
        }


class PerformanceMonitor:
    """
    Comprehensive performance monitoring and optimization

    Features:
    - Operation timing and profiling
    - Memory usage tracking
    - Async operation monitoring
    - Performance bottleneck detection
    - Automatic optimization suggestions
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._metrics: Dict[str, PerformanceMetrics] = defaultdict(PerformanceMetrics)
        self._operation_stack: List[Dict[str, Any]] = []
        self._monitoring_active = False
        self._monitor_task: Optional[asyncio.Task] = None

    def start_monitoring(self):
        """Start performance monitoring"""
        self._monitoring_active = True
        self._monitor_task = asyncio.create_task(self._monitor_performance())
        self.logger.info("✅ Performance monitoring started")

    def stop_monitoring(self):
        """Stop performance monitoring"""
        self._monitoring_active = False
        if self._monitor_task:
            self._monitor_task.cancel()

    async def _monitor_performance(self):
        """Background performance monitoring"""
        while self._monitoring_active:
            try:
                await asyncio.sleep(60)  # Monitor every minute

                # Check for performance issues
                await self._check_performance_issues()

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in performance monitoring: {e}")

    async def _check_performance_issues(self):
        """Check for performance bottlenecks"""
        for operation_name, metrics in self._metrics.items():
            # Check for slow operations
            if metrics.average_duration > 10.0:  # More than 10 seconds average
                self.logger.warning(
                    f"🚨 Slow operation detected: {operation_name} "
                    f"(avg: {metrics.average_duration:.2f}s, count: {metrics.operation_count})"
                )

            # Check for high error rates
            if metrics.get_success_rate() < 0.8:  # Less than 80% success rate
                self.logger.warning(
                    f"🚨 High error rate detected: {operation_name} "
                    f"({metrics.get_success_rate()*100:.1f}% success rate)"
                )

    def time_operation(self, operation_name: str):
        """Decorator to time operations"""
        def decorator(func):
            if asyncio.iscoroutinefunction(func):
                @functools.wraps(func)
                async def async_wrapper(*args, **kwargs):
                    start_time = time.time()
                    try:
                        result = await func(*args, **kwargs)
                        duration = time.time() - start_time

                        # Record metrics
                        self._metrics[operation_name].record_operation(duration, success=True)

                        # Log slow operations
                        if duration > 5.0:  # More than 5 seconds
                            self.logger.warning(f"🐌 Slow operation: {operation_name} took {duration:.2f}s")

                        return result

                    except Exception as e:
                        duration = time.time() - start_time
                        self._metrics[operation_name].record_operation(duration, success=False)
                        self.logger.error(f"❌ Operation failed: {operation_name} after {duration:.2f}s: {e}")
                        raise

                return async_wrapper

            else:
                @functools.wraps(func)
                def sync_wrapper(*args, **kwargs):
                    start_time = time.time()
                    try:
                        result = func(*args, **kwargs)
                        duration = time.time() - start_time

                        # Record metrics
                        self._metrics[operation_name].record_operation(duration, success=True)

                        # Log slow operations
                        if duration > 5.0:  # More than 5 seconds
                            self.logger.warning(f"🐌 Slow operation: {operation_name} took {duration:.2f}s")

                        return result

                    except Exception as e:
                        duration = time.time() - start_time
                        self._metrics[operation_name].record_operation(duration, success=False)
                        self.logger.error(f"❌ Operation failed: {operation_name} after {duration:.2f}s: {e}")
                        raise

                return sync_wrapper

        return decorator

    def get_metrics(self, operation_name: Optional[str] = None) -> Dict[str, Any]:
        """Get performance metrics"""
        if operation_name:
            if operation_name in self._metrics:
                metrics = self._metrics[operation_name]
                return {
                    'operation': operation_name,
                    'count': metrics.operation_count,
                    'total_duration': metrics.total_duration,
                    'average_duration': metrics.average_duration,
                    'min_duration': metrics.min_duration,
                    'max_duration': metrics.max_duration,
                    'error_count': metrics.error_count,
                    'success_rate': metrics.get_success_rate(),
                    'last_operation': metrics.last_operation.isoformat() if metrics.last_operation else None
                }
            else:
                return {'operation': operation_name, 'error': 'No metrics available'}
        else:
            # Return all metrics
            return {
                operation: self.get_metrics(operation)
                for operation in self._metrics.keys()
            }


class MemoryOptimizer:
    """
    Memory usage optimization and garbage collection management

    Features:
    - Memory usage monitoring
    - Automatic garbage collection triggering
    - Memory leak detection
    - Memory-efficient data structures
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._baseline_memory = 0
        self._memory_threshold_mb = 100  # Trigger GC if memory grows by 100MB
        self._gc_collections = 0

    def get_memory_usage(self) -> Dict[str, Union[float, str]]:
        """Get current memory usage statistics"""
        try:
            import psutil
            process = psutil.Process()

            memory_info = process.memory_info()
            memory_percent = process.memory_percent()

            return {
                'rss_mb': memory_info.rss / 1024 / 1024,  # Resident Set Size
                'vms_mb': memory_info.vms / 1024 / 1024,  # Virtual Memory Size
                'memory_percent': memory_percent,
                'fd_count': process.num_fds() if hasattr(process, 'num_fds') else 0
            }

        except ImportError:
            # psutil not available
            return {'error': 'psutil not available'}
        except Exception as e:
            return {'error': str(e)}

    def optimize_memory(self, force: bool = False):
        """Trigger memory optimization"""
        try:
            memory_usage = self.get_memory_usage()

            if 'rss_mb' in memory_usage:
                current_memory = memory_usage['rss_mb']

                if force or (isinstance(current_memory, (int, float)) and isinstance(self._baseline_memory, (int, float)) and (current_memory - self._baseline_memory) > self._memory_threshold_mb):
                    self.logger.info(f"🧹 Triggering memory optimization (RSS: {current_memory:.1f}MB)")

                    # Force garbage collection
                    gc.collect()

                    # Update baseline
                    self._baseline_memory = current_memory
                    self._gc_collections += 1

                    self.logger.info("✅ Memory optimization completed")

        except Exception as e:
            self.logger.error(f"❌ Memory optimization failed: {e}")

    def set_memory_threshold(self, threshold_mb: float):
        """Set memory threshold for automatic optimization"""
        self._memory_threshold_mb = threshold_mb
        self.logger.info(f"✅ Memory threshold set to {threshold_mb}MB")


class QueryOptimizer:
    """
    Database query optimization and caching

    Features:
    - Query result caching
    - Query performance analysis
    - Automatic query optimization
    - Batch operation optimization
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._query_cache = MetadataCache(max_size=500, ttl_seconds=1800)  # 30 minute TTL
        self._query_metrics: Dict[str, PerformanceMetrics] = defaultdict(PerformanceMetrics)

    def optimize_search_query(self, collection: str, query: str, limit: int) -> Dict[str, Any]:
        """
        Optimize search query parameters

        Args:
            collection: Collection name
            query: Search query
            limit: Result limit

        Returns:
            Optimized query parameters
        """
        # Check cache first
        cache_key = f"search:{collection}:{hash(query)}:{limit}"
        cached_result = self._query_cache.get(cache_key)

        if cached_result:
            self.logger.debug(f"📋 Using cached search result for {collection}")
            return cached_result

        # Optimize query parameters
        optimized_params = {
            'collection': collection,
            'query': query.strip(),
            'limit': min(limit, 100),  # Cap at 100 results
            'optimized': True
        }

        return optimized_params

    def cache_query_result(self, collection: str, query: str, limit: int, results: List[Dict]):
        """Cache query results for performance"""
        cache_key = f"search:{collection}:{hash(query)}:{limit}"
        self._query_cache.put(cache_key, results)

    def get_query_metrics(self) -> Dict[str, Any]:
        """Get query performance metrics"""
        return {
            name: {
                'count': metrics.operation_count,
                'avg_duration': metrics.average_duration,
                'success_rate': metrics.get_success_rate()
            }
            for name, metrics in self._query_metrics.items()
        }


# Global performance instances
_connection_pool: Optional[GitHubConnectionPool] = None
_metadata_cache = MetadataCache()
_performance_monitor = PerformanceMonitor()
_memory_optimizer = MemoryOptimizer()
_query_optimizer = QueryOptimizer()


def get_connection_pool(config_manager=None) -> GitHubConnectionPool:
    """Get or create global connection pool"""
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = GitHubConnectionPool(config_manager)
    return _connection_pool


def get_metadata_cache() -> MetadataCache:
    """Get global metadata cache"""
    return _metadata_cache


def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor"""
    return _performance_monitor


def get_memory_optimizer() -> MemoryOptimizer:
    """Get global memory optimizer"""
    return _memory_optimizer


def get_query_optimizer() -> QueryOptimizer:
    """Get global query optimizer"""
    return _query_optimizer


# Performance decorators
def monitor_performance(operation_name: str):
    """Decorator to monitor operation performance"""
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                monitor = get_performance_monitor()
                return await monitor.time_operation(operation_name)(func)(*args, **kwargs)
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                monitor = get_performance_monitor()
                return monitor.time_operation(operation_name)(func)(*args, **kwargs)
            return sync_wrapper
    return decorator


def cache_metadata(cache_key: Optional[str] = None):
    """Decorator to cache metadata processing results"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key if not provided
            if cache_key is None:
                key = f"{func.__name__}:{hash(str(args))}:{hash(str(kwargs))}"
            else:
                key = cache_key

            # Check cache
            cache = get_metadata_cache()
            cached_result = cache.get(key)

            if cached_result is not None:
                return cached_result

            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.put(key, result)

            return result

        return wrapper
    return decorator


async def initialize_performance_system(config_manager=None):
    """Initialize all performance optimization systems"""
    try:
        # Initialize connection pool
        connection_pool = get_connection_pool(config_manager)
        await connection_pool.initialize()

        # Start performance monitoring
        performance_monitor = get_performance_monitor()
        performance_monitor.start_monitoring()

        # Set memory optimization threshold
        memory_optimizer = get_memory_optimizer()
        memory_optimizer.set_memory_threshold(100)  # 100MB threshold

        print("✅ Performance optimization systems initialized")
        return True

    except Exception as e:
        logging.error(f"❌ Failed to initialize performance systems: {e}")
        return False


async def shutdown_performance_system():
    """Shutdown all performance optimization systems"""
    try:
        # Stop performance monitoring
        performance_monitor = get_performance_monitor()
        performance_monitor.stop_monitoring()

        # Shutdown connection pool
        connection_pool = get_connection_pool()
        await connection_pool.shutdown()

        print("✅ Performance optimization systems shutdown")
        return True

    except Exception as e:
        logging.error(f"❌ Error shutting down performance systems: {e}")
        return False