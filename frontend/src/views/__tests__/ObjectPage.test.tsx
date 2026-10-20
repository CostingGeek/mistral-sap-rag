import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import ObjectPage from '../ObjectPage';

// Mock the useApi hook
vi.mock('../../hooks/useApi', () => ({
  useApi: () => ({
    getObject: vi.fn(),
    getObjectGraph: vi.fn()
  })
}));

// Mock ResizeObserver for components that use it
class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
global.ResizeObserver = ResizeObserver;

describe('ObjectPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderWithRouter = (objectId: string) => {
    return render(
      <MemoryRouter initialEntries={[`/object/${encodeURIComponent(objectId)}`]}>
        <Routes>
          <Route path="/object/:objectId" element={<ObjectPage />} />
        </Routes>
      </MemoryRouter>
    );
  };

  it('displays loading state', async () => {
    // Mock useApi to return loading state
    vi.doMock('../../hooks/useApi', () => ({
      useApi: () => ({
        getObject: vi.fn().mockImplementation(() => new Promise(() => {})),
        getObjectGraph: vi.fn().mockImplementation(() => new Promise(() => {}))
      })
    }));

    renderWithRouter('SIMG/TEST/001');
    
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('displays error state', async () => {
    vi.doMock('../../hooks/useApi', () => ({
      useApi: () => ({
        getObject: vi.fn().mockRejectedValue(new Error('Failed to load')),
        getObjectGraph: vi.fn().mockRejectedValue(new Error('Failed to load'))
      })
    }));

    renderWithRouter('SIMG/TEST/001');
    
    await waitFor(() => {
      expect(screen.getByText('Error')).toBeInTheDocument();
      expect(screen.getByText('Failed to load object')).toBeInTheDocument();
    });
  });

  it('displays not found state', async () => {
    vi.doMock('../../hooks/useApi', () => ({
      useApi: () => ({
        getObject: vi.fn().mockResolvedValue({ data: null, error: null }),
        getObjectGraph: vi.fn().mockResolvedValue({ data: null, error: null })
      })
    }));

    renderWithRouter('NONEXISTENT');
    
    await waitFor(() => {
      expect(screen.getByText('Object Not Found')).toBeInTheDocument();
      expect(screen.getByText(/The SAP object "NONEXISTENT" could not be found/)).toBeInTheDocument();
    });
  });

  it('displays object information when loaded', async () => {
    const mockObject = {
      object_id: 'SIMG/TEST/001',
      title: 'Test Object Title',
      sections: {
        'USE': 'Use section content',
        'SHORTTEXT': 'Short text content'
      },
      element_refs: ['activity:SIMG/TEST/002']
    };

    const mockGraph = {
      nodes: [
        { id: 'SIMG/TEST/001', title: 'Test Object Title' },
        { id: 'SIMG/TEST/002', title: 'Related Object' }
      ],
      edges: [
        { source: 'SIMG/TEST/001', target: 'SIMG/TEST/002', type: 'activity' }
      ]
    };

    vi.doMock('../../hooks/useApi', () => ({
      useApi: () => ({
        getObject: vi.fn().mockResolvedValue({ data: mockObject, error: null }),
        getObjectGraph: vi.fn().mockResolvedValue({ data: mockGraph, error: null })
      })
    }));

    renderWithRouter('SIMG/TEST/001');
    
    await waitFor(() => {
      // Should display object title
      expect(screen.getByText('Test Object Title')).toBeInTheDocument();
      
      // Should display object ID
      expect(screen.getByText('SIMG/TEST/001')).toBeInTheDocument();
      
      // Should display sections
      expect(screen.getByText('USE')).toBeInTheDocument();
      expect(screen.getByText('SHORTTEXT')).toBeInTheDocument();
    });
  });

  it('displays related objects', async () => {
    const mockObject = {
      object_id: 'SIMG/TEST/001',
      title: 'Test Object',
      sections: {},
      element_refs: []
    };

    const mockGraph = {
      nodes: [
        { id: 'SIMG/TEST/001', title: 'Test Object' },
        { id: 'SIMG/TEST/002', title: 'Related Object 1' },
        { id: 'SIMG/TEST/003', title: 'Related Object 2' }
      ],
      edges: [
        { source: 'SIMG/TEST/001', target: 'SIMG/TEST/002', type: 'activity' },
        { source: 'SIMG/TEST/001', target: 'SIMG/TEST/003', type: 'activity' }
      ]
    };

    vi.doMock('../../hooks/useApi', () => ({
      useApi: () => ({
        getObject: vi.fn().mockResolvedValue({ data: mockObject, error: null }),
        getObjectGraph: vi.fn().mockResolvedValue({ data: mockGraph, error: null })
      })
    }));

    renderWithRouter('SIMG/TEST/001');
    
    await waitFor(() => {
      expect(screen.getByText('Related Objects')).toBeInTheDocument();
      expect(screen.getByText('Related Object 1')).toBeInTheDocument();
      expect(screen.getByText('Related Object 2')).toBeInTheDocument();
    });
  });

  it('displays no related objects message', async () => {
    const mockObject = {
      object_id: 'SIMG/TEST/001',
      title: 'Test Object',
      sections: {},
      element_refs: []
    };

    const mockGraph = {
      nodes: [],
      edges: []
    };

    vi.doMock('../../hooks/useApi', () => ({
      useApi: () => ({
        getObject: vi.fn().mockResolvedValue({ data: mockObject, error: null }),
        getObjectGraph: vi.fn().mockResolvedValue({ data: mockGraph, error: null })
      })
    }));

    renderWithRouter('SIMG/TEST/001');
    
    await waitFor(() => {
      expect(screen.getByText('No related objects found')).toBeInTheDocument();
    });
  });

  it('displays element references', async () => {
    const mockObject = {
      object_id: 'SIMG/TEST/001',
      title: 'Test Object',
      sections: {},
      element_refs: ['activity:SIMG/TEST/002', 'activity:SIMG/TEST/003']
    };

    const mockGraph = {
      nodes: [],
      edges: []
    };

    vi.doMock('../../hooks/useApi', () => ({
      useApi: () => ({
        getObject: vi.fn().mockResolvedValue({ data: mockObject, error: null }),
        getObjectGraph: vi.fn().mockResolvedValue({ data: mockGraph, error: null })
      })
    }));

    renderWithRouter('SIMG/TEST/001');
    
    await waitFor(() => {
      expect(screen.getByText('References')).toBeInTheDocument();
      expect(screen.getByText('activity:SIMG/TEST/002')).toBeInTheDocument();
      expect(screen.getByText('activity:SIMG/TEST/003')).toBeInTheDocument();
    });
  });

  it('displays no references message', async () => {
    const mockObject = {
      object_id: 'SIMG/TEST/001',
      title: 'Test Object',
      sections: {},
      element_refs: []
    };

    const mockGraph = {
      nodes: [],
      edges: []
    };

    vi.doMock('../../hooks/useApi', () => ({
      useApi: () => ({
        getObject: vi.fn().mockResolvedValue({ data: mockObject, error: null }),
        getObjectGraph: vi.fn().mockResolvedValue({ data: mockGraph, error: null })
      })
    }));

    renderWithRouter('SIMG/TEST/001');
    
    await waitFor(() => {
      expect(screen.getByText('No references')).toBeInTheDocument();
    });
  });

  it('has back link', async () => {
    const mockObject = {
      object_id: 'SIMG/TEST/001',
      title: 'Test Object',
      sections: {},
      element_refs: []
    };

    const mockGraph = {
      nodes: [],
      edges: []
    };

    vi.doMock('../../hooks/useApi', () => ({
      useApi: () => ({
        getObject: vi.fn().mockResolvedValue({ data: mockObject, error: null }),
        getObjectGraph: vi.fn().mockResolvedValue({ data: mockGraph, error: null })
      })
    }));

    renderWithRouter('SIMG/TEST/001');
    
    await waitFor(() => {
      const backLink = screen.getByText('Back');
      expect(backLink).toBeInTheDocument();
      expect(backLink.closest('a')).toHaveAttribute('href', '/');
    });
  });

  it('handles object IDs with special characters', async () => {
    const mockObject = {
      object_id: 'SIMG/SEHS/DG_020',
      title: 'Dangerous Goods',
      sections: { 'USE': 'Use content' },
      element_refs: []
    };

    const mockGraph = {
      nodes: [{ id: 'SIMG/SEHS/DG_020', title: 'Dangerous Goods' }],
      edges: []
    };

    vi.doMock('../../hooks/useApi', () => ({
      useApi: () => ({
        getObject: vi.fn().mockResolvedValue({ data: mockObject, error: null }),
        getObjectGraph: vi.fn().mockResolvedValue({ data: mockGraph, error: null })
      })
    }));

    renderWithRouter('SIMG/SEHS/DG_020');
    
    await waitFor(() => {
      expect(screen.getByText('Dangerous Goods')).toBeInTheDocument();
      expect(screen.getByText('SIMG/SEHS/DG_020')).toBeInTheDocument();
    });
  });
});
