// Test setup for frontend tests
import { expect } from 'vitest';

// Extend expect with custom matchers if needed
// Add global test utilities here

// Mock CSS modules
vi.mock('module.css', () => ({}));

// Mock environment
process.env.NODE_ENV = 'test';
