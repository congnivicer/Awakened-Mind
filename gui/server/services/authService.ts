import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import { AuthRequest } from '../middleware/auth';

/**
 * User roles and permissions
 */
export enum UserRole {
  USER = 'user',
  MODERATOR = 'moderator',
  ADMIN = 'admin'
}

export enum Permission {
  // Document permissions
  READ_DOCUMENTS = 'read:documents',
  CREATE_DOCUMENTS = 'create:documents',
  UPDATE_DOCUMENTS = 'update:documents',
  DELETE_DOCUMENTS = 'delete:documents',

  // Collection permissions
  READ_COLLECTIONS = 'read:collections',
  MANAGE_COLLECTIONS = 'manage:collections',

  // Search permissions
  SEARCH_ALL = 'search:all',
  SEARCH_PUBLIC = 'search:public',

  // Admin permissions
  MANAGE_USERS = 'manage:users',
  VIEW_LOGS = 'view:logs',
  SYSTEM_CONFIG = 'system:config'
}

/**
 * Role-based permissions mapping
 */
const ROLE_PERMISSIONS: Record<UserRole, Permission[]> = {
  [UserRole.USER]: [
    Permission.READ_DOCUMENTS,
    Permission.CREATE_DOCUMENTS,
    Permission.SEARCH_PUBLIC
  ],
  [UserRole.MODERATOR]: [
    Permission.READ_DOCUMENTS,
    Permission.CREATE_DOCUMENTS,
    Permission.UPDATE_DOCUMENTS,
    Permission.DELETE_DOCUMENTS,
    Permission.READ_COLLECTIONS,
    Permission.MANAGE_COLLECTIONS,
    Permission.SEARCH_ALL,
    Permission.VIEW_LOGS
  ],
  [UserRole.ADMIN]: [
    ...Object.values(Permission) // All permissions
  ]
};

/**
 * User interface
 */
export interface User {
  id: string;
  email: string;
  role: UserRole;
  isActive: boolean;
  lastLogin?: Date;
  createdAt: Date;
  updatedAt: Date;
  passwordHash?: string; // Only present during creation/update
}

/**
 * Authentication service for user management and JWT operations
 */
export class AuthenticationService {
  private jwtSecret: string | undefined;
  private jwtExpiresIn: string;
  private saltRounds: number;

  // In-memory user store (replace with database in production)
  private users: Map<string, User> = new Map();

  constructor() {
    this.jwtSecret = process.env.JWT_SECRET;
    this.jwtExpiresIn = process.env.JWT_EXPIRES_IN || '24h';
    this.saltRounds = 12;

    if (!this.jwtSecret) {
      throw new Error(
        'JWT_SECRET environment variable is required for security. ' +
        'Please set it to a secure random string (minimum 32 characters). ' +
        'Generate with: node -e "console.log(require(\'crypto\').randomBytes(64).toString(\'hex\'))"'
      );
    }

    console.log('[AUTHSERVICE] JWT configuration validated successfully:', {
      jwtExpiresIn: this.jwtExpiresIn,
      saltRounds: this.saltRounds,
      nodeEnv: process.env.NODE_ENV,
      userCount: this.users.size
    });

    if (this.jwtSecret === 'fallback-secret-change-in-production') {
      console.warn('⚠️  WARNING: Using fallback JWT secret. Set JWT_SECRET environment variable!');
    }

    // Initialize with default admin user for development
    this.initializeDefaultUsers();
  }

  /**
   * Initialize default users for development
   */
  private async initializeDefaultUsers(): Promise<void> {
    if (process.env.NODE_ENV === 'production') return;

    const defaultAdminUser = {
      id: 'admin-001',
      email: 'admin@localhost',
      role: UserRole.ADMIN,
      isActive: true,
      createdAt: new Date(),
      updatedAt: new Date(),
      passwordHash: await this.hashPassword('password123')
    };

    const defaultRegularUser = {
      id: 'user-001',
      email: 'user@localhost',
      role: UserRole.USER,
      isActive: true,
      createdAt: new Date(),
      updatedAt: new Date(),
      passwordHash: await this.hashPassword('password123')
    };

    if (!this.users.has(defaultAdminUser.id)) {
      this.users.set(defaultAdminUser.id, defaultAdminUser);
    }

    if (!this.users.has(defaultRegularUser.id)) {
      this.users.set(defaultRegularUser.id, defaultRegularUser);
    }
  }

  /**
   * Hash password using bcrypt
   */
  async hashPassword(password: string): Promise<string> {
    try {
      const salt = await bcrypt.genSalt(this.saltRounds);
      return await bcrypt.hash(password, salt);
    } catch (error) {
      throw new Error('Failed to hash password');
    }
  }

  /**
   * Verify password against hash
   */
  async verifyPassword(password: string, hash: string): Promise<boolean> {
    try {
      return await bcrypt.compare(password, hash);
    } catch (error) {
      throw new Error('Failed to verify password');
    }
  }

  /**
   * Generate JWT token for user
   */
  generateToken(user: User): string {
    const payload = {
      id: user.id,
      email: user.email,
      role: user.role,
      permissions: ROLE_PERMISSIONS[user.role],
      isActive: user.isActive
    };

    if (!this.jwtSecret) {
      throw new Error('JWT secret not configured');
    }

    return jwt.sign(payload, this.jwtSecret as jwt.Secret, {
      expiresIn: this.jwtExpiresIn,
      issuer: 'nhb-knowledge-infrastructure',
      audience: 'nhb-api-users',
      subject: user.id
    } as jwt.SignOptions);
  }

  /**
   * Verify and decode JWT token
   */
  verifyToken(token: string): any {
    try {
      return jwt.verify(token, this.jwtSecret);
    } catch (error: any) {
      if (error.name === 'TokenExpiredError') {
        throw new Error('Token has expired');
      }
      if (error.name === 'JsonWebTokenError') {
        throw new Error('Invalid token');
      }
      throw new Error('Token verification failed');
    }
  }

  /**
   * Authenticate user with email and password
   */
  async authenticateUser(email: string, password: string): Promise<{ user: User; token: string } | null> {
    try {
      // Input validation
      if (!email || typeof email !== 'string' || !password || typeof password !== 'string') {
        console.log('[AUTH_DEBUG] Invalid input types for authentication');
        return null;
      }

      const sanitizedEmail = email.toLowerCase().trim();
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(sanitizedEmail)) {
        console.log('[AUTH_DEBUG] Invalid email format');
        return null;
      }

      // Find user by email
      let user: User | undefined;
      for (const [id, userData] of this.users.entries()) {
        if (userData.email === sanitizedEmail && userData.isActive) {
          user = userData;
          break;
        }
      }

      if (!user || !user.passwordHash) {
        console.log('[AUTH_DEBUG] User not found or inactive:', { email: sanitizedEmail, found: !!user });
        return null; // User not found or no password set
      }

      // Verify password
      const isValidPassword = await this.verifyPassword(password, user.passwordHash);
      if (!isValidPassword) {
        console.log('[AUTH_DEBUG] Invalid password for user:', sanitizedEmail);
        return null; // Invalid password
      }

      // Update last login
      user.lastLogin = new Date();
      this.users.set(user.id, user);

      // Generate new token
      const token = this.generateToken(user);

      console.log('[AUTH_DEBUG] Successful authentication:', { userId: user.id, email: sanitizedEmail });
      return { user, token };
    } catch (error) {
      console.error('[AUTH_ERROR] Authentication error:', error);
      return null;
    }
  }

  /**
   * Register new user
   */
  async registerUser(email: string, password: string, role: UserRole = UserRole.USER): Promise<User> {
    try {
      // Check if user already exists
      for (const user of this.users.values()) {
        if (user.email === email) {
          throw new Error('User already exists with this email');
        }
      }

      // Hash password
      const passwordHash = await this.hashPassword(password);

      // Create new user
      const user: User = {
        id: `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        email,
        role,
        isActive: true,
        createdAt: new Date(),
        updatedAt: new Date(),
        passwordHash
      };

      // Store user
      this.users.set(user.id, user);

      return user;
    } catch (error) {
      throw new Error(`Registration failed: ${error.message}`);
    }
  }

  /**
   * Get user by ID
   */
  getUserById(id: string): User | null {
    return this.users.get(id) || null;
  }

  /**
   * Get user by email
   */
  getUserByEmail(email: string): User | null {
    for (const user of this.users.values()) {
      if (user.email === email) {
        return user;
      }
    }
    return null;
  }

  /**
   * Update user information
   */
  async updateUser(id: string, updates: Partial<User>): Promise<User | null> {
    const user = this.users.get(id);
    if (!user) {
      return null;
    }

    try {
      // Update user data
      const updatedUser = {
        ...user,
        ...updates,
        updatedAt: new Date()
      };

      // If password is being updated, hash it
      if (updates.passwordHash) {
        // This should be a hashed password already
      }

      this.users.set(id, updatedUser);
      return updatedUser;
    } catch (error) {
      throw new Error(`Failed to update user: ${error.message}`);
    }
  }

  /**
   * Delete user (soft delete by deactivating)
   */
  async deleteUser(id: string): Promise<boolean> {
    const user = this.users.get(id);
    if (!user) {
      return false;
    }

    user.isActive = false;
    user.updatedAt = new Date();
    this.users.set(id, user);
    return true;
  }

  /**
   * Check if user has specific permission
   */
  hasPermission(user: User, permission: Permission): boolean {
    const userPermissions = ROLE_PERMISSIONS[user.role] || [];
    return userPermissions.includes(permission);
  }

  /**
   * Check if user has any of the specified permissions
   */
  hasAnyPermission(user: User, permissions: Permission[]): boolean {
    return permissions.some(permission => this.hasPermission(user, permission));
  }

  /**
   * Check if user has all specified permissions
   */
  hasAllPermissions(user: User, permissions: Permission[]): boolean {
    return permissions.every(permission => this.hasPermission(user, permission));
  }

  /**
   * Get all permissions for a role
   */
  getRolePermissions(role: UserRole): Permission[] {
    return ROLE_PERMISSIONS[role] || [];
  }

  /**
   * List all users (admin only)
   */
  listUsers(): User[] {
    return Array.from(this.users.values()).filter(user => user.isActive);
  }

  /**
   * Refresh JWT token
   */
  refreshToken(token: string): string | null {
    try {
      const decoded = this.verifyToken(token);

      // Get fresh user data
      const user = this.getUserById(decoded.sub || decoded.id);
      if (!user || !user.isActive) {
        return null;
      }

      // Generate new token
      return this.generateToken(user);
    } catch (error) {
      return null;
    }
  }

  /**
   * Validate token and return user info
   */
  validateToken(token: string): { user: User; permissions: Permission[] } | null {
    try {
      const decoded = this.verifyToken(token);

      // Get user data
      const user = this.getUserById(decoded.sub || decoded.id);
      if (!user || !user.isActive) {
        return null;
      }

      const permissions = ROLE_PERMISSIONS[user.role] || [];

      return { user, permissions };
    } catch (error) {
      return null;
    }
  }

  /**
   * Change user password
   */
  async changePassword(userId: string, currentPassword: string, newPassword: string): Promise<boolean> {
    const user = this.users.get(userId);
    if (!user || !user.passwordHash) {
      return false;
    }

    // Verify current password
    const isValidCurrentPassword = await this.verifyPassword(currentPassword, user.passwordHash);
    if (!isValidCurrentPassword) {
      return false;
    }

    // Hash new password
    const newPasswordHash = await this.hashPassword(newPassword);

    // Update user
    user.passwordHash = newPasswordHash;
    user.updatedAt = new Date();
    this.users.set(userId, user);

    return true;
  }

  /**
   * Reset user password (admin function)
   */
  async resetPassword(userId: string, newPassword: string): Promise<boolean> {
    const user = this.users.get(userId);
    if (!user) {
      return false;
    }

    // Hash new password
    const newPasswordHash = await this.hashPassword(newPassword);

    // Update user
    user.passwordHash = newPasswordHash;
    user.updatedAt = new Date();
    this.users.set(userId, user);

    return true;
  }

  /**
   * Get user statistics
   */
  getUserStats(): { total: number; active: number; byRole: Record<UserRole, number> } {
    const users = Array.from(this.users.values());
    const activeUsers = users.filter(user => user.isActive);

    const byRole = {
      [UserRole.USER]: 0,
      [UserRole.MODERATOR]: 0,
      [UserRole.ADMIN]: 0
    };

    activeUsers.forEach(user => {
      byRole[user.role]++;
    });

    return {
      total: users.length,
      active: activeUsers.length,
      byRole
    };
  }
}

// Export singleton instance
export const authService = new AuthenticationService();