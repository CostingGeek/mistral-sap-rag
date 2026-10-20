import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useApi } from '../useApi';

// Mock global fetch
global.fetch = vi.fn();

describe('useApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('returns API methods', () => {
    const { result } = renderHook(() => useApi());
    
    expect(result.current.chat).toBeDefined();
    expect(result.current.getObject).toBeDefined();
    expect(result.current.getObjectGraph).toBeDefined();
    expect(result.current.healthCheck).toBeDefined();
    expect(result.current.request).toBeDefined();
  });

  describe('request method', () => {
    it('makes GET request', async () => {
      const mockResponse = { data: { test: 'value' } };
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockResponse)
      });

      const { result } = renderHook(() => useApi());
      
      const response = await result.current.request('GET', '/test');
      
      expect(global.fetch).toHaveBeenCalledWith('/api/test', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      expect(response.data).toEqual(mockResponse);
    });

    it('makes POST request with data', async () => {
      const mockResponse = { data: { test: 'value' } };
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockResponse)
      });

      const { result } = renderHook(() => useApi());
      
      const data = { message: 'test', scope: 'both' };
      const response = await result.current.request('POST', '/chat', data);
      
      expect(global.fetch).toHaveBeenCalledWith('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
      });
      expect(response.data).toEqual(mockResponse);
    });

    it('handles successful response', async () => {
      const mockResponse = { data: { test: 'value' } };
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockResponse)
      });

      const { result } = renderHook(() => useApi());
      
      const response = await result.current.request('GET', '/test');
      
      expect(response.error).toBeUndefined();
      expect(response.data).toEqual(mockResponse);
    });

    it('handles error response', async () => {
      const mockError = { detail: 'Not found' };
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: false,
        json: () => Promise.resolve(mockError)
      });

      const { result } = renderHook(() => useApi());
      
      const response = await result.current.request('GET', '/not-found');
      
      expect(response.error).toBe('Not found');
      expect(response.data).toBeUndefined();
    });

    it('handles network error', async () => {
      (global.fetch as jest.Mock).mockRejectedValue(new Error('Network error'));

      const { result } = renderHook(() => useApi());
      
      const response = await result.current.request('GET', '/test');
      
      expect(response.error).toBe('Network error');
      expect(response.data).toBeUndefined();
    });

    it('handles non-JSON error response', async () => {
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: false,
        json: () => Promise.reject(new Error('Invalid JSON'))
      });

      const { result } = renderHook(() => useApi());
      
      const response = await result.current.request('GET', '/test');
      
      // Should handle gracefully
      expect(response.error).toBeDefined();
    });

    it('passes abort signal', async () => {
      const mockResponse = { data: { test: 'value' } };
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockResponse)
      });

      const { result } = renderHook(() => useApi());
      
      const controller = new AbortController();
      await result.current.request('GET', '/test', undefined, controller.signal);
      
      expect(global.fetch).toHaveBeenCalledWith('/api/test', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        signal: controller.signal
      });
    });

    it('re-throws AbortError', async () => {
      const abortError = new Error('Aborted');
      abortError.name = 'AbortError';
      (global.fetch as jest.Mock).mockRejectedValue(abortError);

      const { result } = renderHook(() => useApi());
      
      const controller = new AbortController();
      
      await expect(
        result.current.request('GET', '/test', undefined, controller.signal)
      ).rejects.toThrow('Aborted');
    });
  });

  describe('chat method', () => {
    it('calls POST /chat', async () => {
      const mockResponse = { data: { message: 'Response' } };
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockResponse)
      });

      const { result } = renderHook(() => useApi());
      
      const data = { message: 'test', scope: 'both' };
      const signal = new AbortController().signal;
      
      await result.current.chat(data, signal);
      
      expect(global.fetch).toHaveBeenCalledWith('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
        signal: signal
      });
    });
  });

  describe('getObject method', () => {
    it('calls GET /object/:id', async () => {
      const mockResponse = { data: { object_id: 'SIMG/TEST/001', title: 'Test' } };
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockResponse)
      });

      const { result } = renderHook(() => useApi());
      
      await result.current.getObject('SIMG/TEST/001');
      
      // encodeURIComponent encodes slashes as %2F
      expect(global.fetch).toHaveBeenCalledWith('/api/object/SIMG%2FTEST%2F001', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });
    });

    it('includes scope parameter', async () => {
      const mockResponse = { data: { object_id: 'SIMG/TEST/001', title: 'Test' } };
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockResponse)
      });

      const { result } = renderHook(() => useApi());
      
      await result.current.getObject('SIMG/TEST/001', 'standard');
      
      // encodeURIComponent encodes slashes as %2F
      expect(global.fetch).toHaveBeenCalledWith('/api/object/SIMG%2FTEST%2F001?scope=standard', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });
    });

    it('handles object IDs with slashes', async () => {
      const mockResponse = { data: { object_id: 'SIMG/SEHS/DG_020', title: 'Test' } };
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockResponse)
      });

      const { result } = renderHook(() => useApi());
      
      await result.current.getObject('SIMG/SEHS/DG_020');
      
      // encodeURIComponent encodes slashes as %2F
      expect(global.fetch).toHaveBeenCalledWith('/api/object/SIMG%2FSEHS%2FDG_020', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });
    });
  });

  describe('getObjectGraph method', () => {
    it('calls GET /object/:id/graph', async () => {
      const mockResponse = { data: { nodes: [], edges: [] } };
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockResponse)
      });

      const { result } = renderHook(() => useApi());
      
      await result.current.getObjectGraph('SIMG/TEST/001');
      
      // encodeURIComponent encodes slashes as %2F
      expect(global.fetch).toHaveBeenCalledWith('/api/object/SIMG%2FTEST%2F001/graph', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });
    });

    it('handles object IDs with slashes in graph', async () => {
      const mockResponse = { data: { nodes: [], edges: [] } };
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockResponse)
      });

      const { result } = renderHook(() => useApi());
      
      await result.current.getObjectGraph('SIMG/SEHS/DG_020');
      
      // encodeURIComponent encodes slashes as %2F
      expect(global.fetch).toHaveBeenCalledWith('/api/object/SIMG%2FSEHS%2FDG_020/graph', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });
    });
  });

  describe('healthCheck method', () => {
    it('calls GET /health', async () => {
      const mockResponse = { data: { status: 'healthy' } };
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockResponse)
      });

      const { result } = renderHook(() => useApi());
      
      await result.current.healthCheck();
      
      expect(global.fetch).toHaveBeenCalledWith('/api/health', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });
    });
  });
});
