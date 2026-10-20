import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import HomePage from '../views/HomePage';

// Mock the useApi hook
vi.mock('../hooks/useApi', () => ({
  useApi: () => ({
    chat: vi.fn().mockResolvedValue({ data: {
      message: 'Test response',
      citations: [],
      matched_objects: [],
      graph_data: { nodes: [], edges: [] },
      trace: []
    } }),
    getObject: vi.fn().mockResolvedValue({ data: null }),
    getObjectGraph: vi.fn().mockResolvedValue({ data: { nodes: [], edges: [] } })
  })
}));

// Mock window.scrollTo
global.window.scrollTo = vi.fn();

// Mock ResizeObserver for components that use it
class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
global.ResizeObserver = ResizeObserver;

describe('HomePage', () => {
  beforeEach(() => {
    // Clear all mocks before each test
    vi.clearAllMocks();
  });

  it('renders without crashing', () => {
    render(<HomePage />);
    expect(screen.getByPlaceholderText(/Ask a question/)).toBeInTheDocument();
  });

  it('displays example queries when no messages', () => {
    render(<HomePage />);
    expect(screen.getByText(/What do you want to configure?/)).toBeInTheDocument();
  });

  it('renders input field and buttons', () => {
    render(<HomePage />);
    
    // Input field
    const input = screen.getByPlaceholderText(/Ask a question/);
    expect(input).toBeInTheDocument();
    
    // Send button
    const sendButton = screen.getByText('Send');
    expect(sendButton).toBeInTheDocument();
    
    // Reset button
    const resetButton = screen.getByText('Reset');
    expect(resetButton).toBeInTheDocument();
    
    // Scope selector
    const scopeSelect = screen.getByLabelText(/Scope:/);
    expect(scopeSelect).toBeInTheDocument();
  });

  it('displays scope options', () => {
    render(<HomePage />);
    
    const scopeSelect = screen.getByLabelText(/Scope:/) as HTMLSelectElement;
    expect(scopeSelect).toBeInTheDocument();
    
    // Check that options exist
    expect(scopeSelect.querySelector('option[value="both"]')).toBeInTheDocument();
    expect(scopeSelect.querySelector('option[value="standard"]')).toBeInTheDocument();
    expect(scopeSelect.querySelector('option[value="nova"]')).toBeInTheDocument();
  });

  it('updates input value on change', () => {
    render(<HomePage />);
    
    const input = screen.getByPlaceholderText(/Ask a question/) as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'Test query' } });
    
    expect(input.value).toBe('Test query');
  });

  it('does not send empty messages', async () => {
    const { useApi } = await import('../hooks/useApi');
    const mockChat = vi.fn().mockResolvedValue({ data: {
      message: 'Response',
      citations: [],
      matched_objects: [],
      graph_data: { nodes: [], edges: [] },
      trace: []
    } });
    
    vi.doMock('../hooks/useApi', () => ({
      useApi: () => ({
        chat: mockChat,
        getObject: vi.fn().mockResolvedValue({ data: null }),
        getObjectGraph: vi.fn().mockResolvedValue({ data: { nodes: [], edges: [] } })
      })
    }));
    
    render(<HomePage />);
    
    const sendButton = screen.getByText('Send');
    fireEvent.click(sendButton);
    
    // Should not call chat API with empty message
    expect(mockChat).not.toHaveBeenCalled();
  });

  it('sends message on Enter key (without Shift)', async () => {
    const { useApi } = await import('../hooks/useApi');
    const mockChat = vi.fn().mockResolvedValue({ data: {
      message: 'Response',
      citations: [],
      matched_objects: [],
      graph_data: { nodes: [], edges: [] },
      trace: []
    } });
    
    vi.doMock('../hooks/useApi', () => ({
      useApi: () => ({
        chat: mockChat,
        getObject: vi.fn().mockResolvedValue({ data: null }),
        getObjectGraph: vi.fn().mockResolvedValue({ data: { nodes: [], edges: [] } })
      })
    }));
    
    render(<HomePage />);
    
    const input = screen.getByPlaceholderText(/Ask a question/) as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'Test query' } });
    
    // Fire Enter key
    fireEvent.keyDown(input, { key: 'Enter', shiftKey: false });
    
    // Should call chat API
    await vi.waitFor(() => {
      expect(mockChat).toHaveBeenCalled();
    });
  });

  it('does not send message on Shift+Enter', async () => {
    const { useApi } = await import('../hooks/useApi');
    const mockChat = vi.fn().mockResolvedValue({ data: {
      message: 'Response',
      citations: [],
      matched_objects: [],
      graph_data: { nodes: [], edges: [] },
      trace: []
    } });
    
    vi.doMock('../hooks/useApi', () => ({
      useApi: () => ({
        chat: mockChat,
        getObject: vi.fn().mockResolvedValue({ data: null }),
        getObjectGraph: vi.fn().mockResolvedValue({ data: { nodes: [], edges: [] } })
      })
    }));
    
    render(<HomePage />);
    
    const input = screen.getByPlaceholderText(/Ask a question/) as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'Test query' } });
    
    // Fire Shift+Enter
    fireEvent.keyDown(input, { key: 'Enter', shiftKey: true });
    
    // Should not call chat API
    expect(mockChat).not.toHaveBeenCalled();
  });

  it('disables send button when loading', async () => {
    const { useApi } = await import('../hooks/useApi');
    let resolveChat: (value: any) => void;
    const mockChat = vi.fn().mockImplementation(() => (
      new Promise(resolve => { resolveChat = resolve; })
    ));
    
    vi.doMock('../hooks/useApi', () => ({
      useApi: () => ({
        chat: mockChat,
        getObject: vi.fn().mockResolvedValue({ data: null }),
        getObjectGraph: vi.fn().mockResolvedValue({ data: { nodes: [], edges: [] } })
      })
    }));
    
    render(<HomePage />);
    
    const input = screen.getByPlaceholderText(/Ask a question/) as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'Test query' } });
    fireEvent.keyDown(input, { key: 'Enter', shiftKey: false });
    
    // Wait for loading state
    await vi.waitFor(() => {
      const sendButton = screen.getByText('Send');
      expect(sendButton).toBeDisabled();
    });
    
    // Resolve the promise
    resolveChat!({ data: {
      message: 'Response',
      citations: [],
      matched_objects: [],
      graph_data: { nodes: [], edges: [] },
      trace: []
    } });
  });

  it('displays assistant messages after chat', async () => {
    const { useApi } = await import('../hooks/useApi');
    const mockChat = vi.fn().mockResolvedValue({ data: {
      message: 'This is a test response',
      citations: [],
      matched_objects: [],
      graph_data: { nodes: [], edges: [] },
      trace: []
    } });
    
    vi.doMock('../hooks/useApi', () => ({
      useApi: () => ({
        chat: mockChat,
        getObject: vi.fn().mockResolvedValue({ data: null }),
        getObjectGraph: vi.fn().mockResolvedValue({ data: { nodes: [], edges: [] } })
      })
    }));
    
    render(<HomePage />);
    
    const input = screen.getByPlaceholderText(/Ask a question/) as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'Test query' } });
    fireEvent.keyDown(input, { key: 'Enter', shiftKey: false });
    
    await vi.waitFor(() => {
      expect(screen.getByText('Assistant')).toBeInTheDocument();
      expect(screen.getByText('This is a test response')).toBeInTheDocument();
    });
  });

  it('displays user messages', async () => {
    const { useApi } = await import('../hooks/useApi');
    const mockChat = vi.fn().mockResolvedValue({ data: {
      message: 'Response',
      citations: [],
      matched_objects: [],
      graph_data: { nodes: [], edges: [] },
      trace: []
    } });
    
    vi.doMock('../hooks/useApi', () => ({
      useApi: () => ({
        chat: mockChat,
        getObject: vi.fn().mockResolvedValue({ data: null }),
        getObjectGraph: vi.fn().mockResolvedValue({ data: { nodes: [], edges: [] } })
      })
    }));
    
    render(<HomePage />);
    
    const input = screen.getByPlaceholderText(/Ask a question/) as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'Test query' } });
    fireEvent.keyDown(input, { key: 'Enter', shiftKey: false });
    
    await vi.waitFor(() => {
      expect(screen.getByText('You')).toBeInTheDocument();
      expect(screen.getByText('Test query')).toBeInTheDocument();
    });
  });

  it('clears input after sending', async () => {
    const { useApi } = await import('../hooks/useApi');
    const mockChat = vi.fn().mockResolvedValue({ data: {
      message: 'Response',
      citations: [],
      matched_objects: [],
      graph_data: { nodes: [], edges: [] },
      trace: []
    } });
    
    vi.doMock('../hooks/useApi', () => ({
      useApi: () => ({
        chat: mockChat,
        getObject: vi.fn().mockResolvedValue({ data: null }),
        getObjectGraph: vi.fn().mockResolvedValue({ data: { nodes: [], edges: [] } })
      })
    }));
    
    render(<HomePage />);
    
    const input = screen.getByPlaceholderText(/Ask a question/) as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'Test query' } });
    expect(input.value).toBe('Test query');
    
    fireEvent.keyDown(input, { key: 'Enter', shiftKey: false });
    
    await vi.waitFor(() => {
      expect(input.value).toBe('');
    });
  });

  it('renders markdown content correctly', async () => {
    const { useApi } = await import('../hooks/useApi');
    const mockChat = vi.fn().mockResolvedValue({ data: {
      message: '# Heading\n\nThis is **bold** text',
      citations: [],
      matched_objects: [],
      graph_data: { nodes: [], edges: [] },
      trace: []
    } });
    
    vi.doMock('../hooks/useApi', () => ({
      useApi: () => ({
        chat: mockChat,
        getObject: vi.fn().mockResolvedValue({ data: null }),
        getObjectGraph: vi.fn().mockResolvedValue({ data: { nodes: [], edges: [] } })
      })
    }));
    
    render(<HomePage />);
    
    const input = screen.getByPlaceholderText(/Ask a question/) as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'Test' } });
    fireEvent.keyDown(input, { key: 'Enter', shiftKey: false });
    
    await vi.waitFor(() => {
      // Check for bold text
      expect(screen.getByText('This is bold text')).toBeInTheDocument();
    });
  });

  it('displays citations when present', async () => {
    const { useApi } = await import('../hooks/useApi');
    const mockChat = vi.fn().mockResolvedValue({ data: {
      message: 'Response with citation',
      citations: [
        {
          chunk_id: 'chunk-1',
          object_id: 'SIMG/TEST/001',
          title: 'Test Object',
          section_type: 'USE',
          distance: 0.1,
          corpus: 'standard',
          graph_expanded: false,
          source_no: 1
        }
      ],
      matched_objects: ['SIMG/TEST/001'],
      graph_data: { nodes: [], edges: [] },
      trace: []
    } });
    
    vi.doMock('../hooks/useApi', () => ({
      useApi: () => ({
        chat: mockChat,
        getObject: vi.fn().mockResolvedValue({ data: null }),
        getObjectGraph: vi.fn().mockResolvedValue({ data: { nodes: [], edges: [] } })
      })
    }));
    
    render(<HomePage />);
    
    const input = screen.getByPlaceholderText(/Ask a question/) as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'Test' } });
    fireEvent.keyDown(input, { key: 'Enter', shiftKey: false });
    
    await vi.waitFor(() => {
      expect(screen.getByText('Sources:')).toBeInTheDocument();
      expect(screen.getByText('SIMG/TEST/001')).toBeInTheDocument();
    });
  });
});
