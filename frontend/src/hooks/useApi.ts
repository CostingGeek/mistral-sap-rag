import { useCallback } from 'react';
import { ApiResponse } from '../types';

const API_BASE = '/api';

export const useApi = () => {
  const request = useCallback(async <T>(
    method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE',
    endpoint: string,
    data?: any
  ): Promise<ApiResponse<T>> => {
    try {
      const options: RequestInit = {
        method,
        headers: {
          'Content-Type': 'application/json',
        },
      };

      if (data && method !== 'GET') {
        options.body = JSON.stringify(data);
      }

      const response = await fetch(`${API_BASE}${endpoint}`, options);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        return {
          error: errorData.detail || errorData.message || 'An error occurred',
        };
      }

      const result = await response.json();
      return { data: result };
    } catch (error) {
      console.error('API request failed:', error);
      return { error: 'Network error' };
    }
  }, []);

  // Specific API methods
  const api = {
    // Chat
    chat: useCallback((data: { message: string; session_id?: string; history?: any[]; scope?: string }) =>
      request<any>('POST', '/chat', data)
    , []),

    // Objects
    getObject: useCallback((objectId: string) =>
      request<any>('GET', `/object/${encodeURIComponent(objectId)}`)
    , []),

    getObjectGraph: useCallback((objectId: string) =>
      request<any>('GET', `/object/${encodeURIComponent(objectId)}/graph`)
    , []),

    // Decisions
    getDecisions: useCallback((sessionId: string) =>
      request<any[]>('GET', `/decisions/${sessionId}`)
    , []),

    updateDecision: useCallback((decisionId: string, data: { status?: string; answer?: string }) =>
      request<any>('PATCH', `/decisions/${decisionId}`, data)
    , []),

    // Health
    healthCheck: useCallback(() =>
      request<any>('GET', '/health')
    , []),
  };

  return { request, ...api };
};

export default useApi;
