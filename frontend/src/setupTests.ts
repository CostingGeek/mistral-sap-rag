// Global test setup for Vitest
import { vi, expect } from 'vitest'
import * as matchers from '@testing-library/jest-dom/matchers'

// Extend Vitest's expect with jest-dom matchers
expect.extend(matchers)

// Mock ResizeObserver for components that use it (e.g., react-flow)
class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
global.ResizeObserver = ResizeObserver

// Mock Element.scrollIntoView for jsdom
// Need to handle both scrollIntoView() and scrollIntoView({ behavior: 'smooth' })
Element.prototype.scrollIntoView = vi.fn((options?: any) => {
  // Mock implementation does nothing
})

// Mock window.scrollTo
global.window.scrollTo = vi.fn()

// Mock requestIdleCallback for some libraries
global.requestIdleCallback = vi.fn((cb: () => void) => cb())
