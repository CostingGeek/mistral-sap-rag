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
    // Sessions
    createSession: useCallback((kind: string, title?: string) =>
      request<{ session_id: string }>('POST', '/sessions', { kind, title })
    , []),

    listSessions: useCallback((limit?: number) =>
      request<any[]>('GET', `/sessions${limit ? `?limit=${limit}` : ''}`)
    , []),

    getSession: useCallback((sessionId: string) =>
      request<any>('GET', `/sessions/${sessionId}`)
    , []),

    clearAllSessions: useCallback(() =>
      request<any>('DELETE', '/sessions')
    , []),

    // Chat
    chat: useCallback((data: { message: string; session_id?: string; history?: any[] }) =>
      request<any>('POST', '/chat', data)
    , []),

    // PDF
    uploadPdf: useCallback((file: File, title?: string, sessionId?: string) => {
      const formData = new FormData();
      formData.append('file', file);
      if (title) {
        formData.append('title', title);
      }
      if (sessionId) {
        formData.append('session_id', sessionId);
      }

      return fetch(`${API_BASE}/upload/pdf`, {
        method: 'POST',
        body: formData,
      }).then(async (response) => {
        if (!response.ok) {
          const error = await response.json().catch(() => ({}));
          return { error: error.detail || 'Upload failed' };
        }
        return { data: await response.json() };
      });
    }, []),

    processPdf: useCallback((sessionId: string) =>
      request<any>('POST', `/sessions/${sessionId}/process-pdf`)
    , []),

    getPdfStatus: useCallback((sessionId: string) =>
      request<any>('GET', `/sessions/${sessionId}/status`)
    , []),

    getReport: useCallback((sessionId: string) =>
      request<any>('GET', `/report/${sessionId}`)
    , []),

    // Objects
    getObject: useCallback((objectId: string) =>
      request<any>('GET', `/object/${objectId}`)
    , []),

    getObjectGraph: useCallback((objectId: string) =>
      request<any>('GET', `/object/${objectId}/graph`)
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
