import { spawn } from 'child_process';
import { promisify } from 'util';
import path from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

export interface PythonExecutionResult {
  success: boolean;
  data?: any;
  error?: string;
  executionTime: number;
}

export interface PythonScriptParams {
  scriptName: string;
  functionName: string;
  parameters: Record<string, any>;
  timeout?: number;
}

/**
 * Secure Python script execution service
 * Replaces dangerous string interpolation with parameterized execution
 */
export class SecurePythonExecutor {
  private projectRoot: string;
  private scriptTimeout: number;

  constructor(projectRoot?: string, scriptTimeout = 30000) {
    this.projectRoot = projectRoot || path.join(__dirname, '../..');
    this.scriptTimeout = scriptTimeout;
  }

  /**
   * Execute Python function securely with parameters
   */
  async executePythonFunction(params: PythonScriptParams): Promise<PythonExecutionResult> {
    const startTime = Date.now();

    try {
      // Validate parameters
      this.validateParameters(params.parameters);

      // Create temporary parameter file for secure data passing
      const paramFile = await this.createParameterFile(params.parameters);

      try {
        // Execute Python script with secure parameter passing
        const result = await this.executeWithParameters(
          params.scriptName,
          params.functionName,
          paramFile,
          params.timeout
        );

        const executionTime = Date.now() - startTime;
        return {
          success: true,
          data: result,
          executionTime
        };

      } finally {
        // Clean up temporary file
        await this.cleanupParameterFile(paramFile);
      }

    } catch (error: any) {
      const executionTime = Date.now() - startTime;
      return {
        success: false,
        error: error.message || 'Unknown execution error',
        executionTime
      };
    }
  }

  /**
   * Validate parameters to prevent injection attacks
   */
  private validateParameters(parameters: Record<string, any>): void {
    const allowedTypes = ['string', 'number', 'boolean'];

    for (const [key, value] of Object.entries(parameters)) {
      // Check for dangerous key patterns
      if (this.containsDangerousPattern(key)) {
        throw new Error(`Dangerous parameter key detected: ${key}`);
      }

      // Validate parameter types
      if (!allowedTypes.includes(typeof value) && value !== null && value !== undefined) {
        throw new Error(`Invalid parameter type for ${key}: ${typeof value}`);
      }

      // Validate string content for injection attempts
      if (typeof value === 'string') {
        if (this.containsDangerousPattern(value)) {
          throw new Error(`Dangerous content detected in parameter ${key}`);
        }
        if (value.length > 10000) {
          throw new Error(`Parameter ${key} exceeds maximum length`);
        }
      }
    }
  }

  /**
   * Check for dangerous patterns that could indicate injection attacks
   */
  private containsDangerousPattern(input: string): boolean {
    const dangerousPatterns = [
      /[<>'"&|`$(){}[\]\\]/,  // Basic injection characters
      /;\s*(rm|cat|wget|curl|python|bash|sh|exec)/i,  // Command injection
      /import\s+(os|subprocess|sys|shutil)/i,  // Dangerous imports
      /__\w+__/,  // Dunder methods that could be exploited
      /eval\s*\(/i,  // Eval function calls
      /exec\s*\(/i,  // Exec function calls
      /system\s*\(/i,  // System calls
    ];

    return dangerousPatterns.some(pattern => pattern.test(input));
  }

  /**
   * Create temporary file with parameters for secure passing to Python
   */
  private async createParameterFile(parameters: Record<string, any>): Promise<string> {
    const fs = await import('fs/promises');
    const crypto = await import('crypto');

    const tempDir = path.join(this.projectRoot, 'temp');
    await fs.mkdir(tempDir, { recursive: true });

    const fileId = crypto.randomBytes(8).toString('hex');
    const paramFile = path.join(tempDir, `params_${fileId}.json`);

    // Create sanitized parameter object
    const sanitizedParams = this.sanitizeParameters(parameters);

    await fs.writeFile(paramFile, JSON.stringify(sanitizedParams, null, 2), {
      mode: 0o600, // Read/write for owner only
      encoding: 'utf8'
    });

    return paramFile;
  }

  /**
   * Sanitize parameters to ensure safe execution
   */
  private sanitizeParameters(parameters: Record<string, any>): Record<string, any> {
    const sanitized: Record<string, any> = {};

    for (const [key, value] of Object.entries(parameters)) {
      // Only allow alphanumeric keys with underscores
      const cleanKey = key.replace(/[^a-zA-Z0-9_]/g, '_');

      if (typeof value === 'string') {
        // Escape quotes and backslashes for safe shell usage
        sanitized[cleanKey] = value
          .replace(/\\/g, '\\\\')
          .replace(/"/g, '\\"')
          .replace(/'/g, "\\'");
      } else {
        sanitized[cleanKey] = value;
      }
    }

    return sanitized;
  }

  /**
   * Execute Python script with secure parameter passing
   */
  private async executeWithParameters(
    scriptName: string,
    functionName: string,
    paramFile: string,
    timeout?: number
  ): Promise<any> {
    return new Promise((resolve, reject) => {
      const scriptPath = path.join(this.projectRoot, 'core', scriptName);

      // Build secure command
      const command = 'python3';
      const args = [
        '-c',
        `
import json
import sys
import os
sys.path.insert(0, '${this.projectRoot.replace(/'/g, "\\'")}')
sys.path.insert(0, '${path.join(this.projectRoot, 'core').replace(/'/g, "\\'")}')

# Load parameters securely
try:
    with open('${paramFile.replace(/'/g, "\\'")}', 'r') as f:
        params = json.load(f)
except Exception as e:
    print(json.dumps({'error': f'Parameter file error: {str(e)}'}))
    sys.exit(1)

# Import and execute function
try:
    from ${scriptName.replace('.py', '')} import ${functionName}
    result = ${functionName}(**params)
    print(json.dumps({'result': result}))
except Exception as e:
    print(json.dumps({'error': str(e)}))
    sys.exit(1)
        `.trim()
      ];

      const pythonProcess = spawn(command, args, {
        stdio: ['ignore', 'pipe', 'pipe'],
        env: {
          ...process.env,
          PYTHONPATH: `${this.projectRoot}:${path.join(this.projectRoot, 'core')}`,
          PYTHONDONTWRITEBYTECODE: '1'
        },
        timeout: timeout || this.scriptTimeout
      });

      let stdout = '';
      let stderr = '';

      pythonProcess.stdout.on('data', (data) => {
        stdout += data.toString();
      });

      pythonProcess.stderr.on('data', (data) => {
        stderr += data.toString();
      });

      pythonProcess.on('close', (code) => {
        if (code === 0 && !stderr) {
          try {
            const output = JSON.parse(stdout);
            if (output.error) {
              reject(new Error(output.error));
            } else {
              resolve(output.result);
            }
          } catch (parseError) {
            reject(new Error(`Failed to parse Python output: ${parseError.message}`));
          }
        } else {
          reject(new Error(`Python execution failed: ${stderr || `Exit code ${code}`}`));
        }
      });

      pythonProcess.on('error', (error) => {
        reject(new Error(`Failed to start Python process: ${error.message}`));
      });
    });
  }

  /**
   * Clean up temporary parameter file
   */
  private async cleanupParameterFile(paramFile: string): Promise<void> {
    try {
      const fs = await import('fs/promises');
      await fs.unlink(paramFile);
    } catch (error) {
      // Log but don't throw - cleanup errors shouldn't break execution
      console.warn(`Failed to cleanup parameter file ${paramFile}:`, error);
    }
  }
}

// Export singleton instance
export const pythonExecutor = new SecurePythonExecutor();