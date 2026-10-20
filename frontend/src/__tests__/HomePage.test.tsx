import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { useApi as useApiType } from '../hooks/useApi';
import HomePage from '../views/HomePage';

// Create a mock for useApi that we can control in tests
const mockUseApi = vi.fn() as jest.MockedFunction<typeof useApiType>;

// Mock the useApi hook to return our controllable mock
vi.mock('../hooks/useApi', () => ({
  useApi: () => mockUseApi()
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

// Default mock response
const defaultMockResponse = {
  chat: vi.fn().mockResolvedValue({ data: {
    message: 'Test response',
    citations: [],
    matched_objects: [],
    graph_data: { nodes: [], edges: [] },
    trace: []
  } }),
  getObject: vi.fn().mockResolvedValue({ data: null }),
  getObjectGraph: vi.fn().mockResolvedValue({ data: { nodes: [], edges: [] } })
};

// Setup default mock before each test
beforeEach(() => {
  mockUseApi.mockReturnValue(defaultMockResponse);
});

afterEach(() => {
  vi.clearAllMocks();
});

describe('HomePage', () => {

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
    render(<HomePage />);
    
    const sendButton = screen.getByText('Send');
    await act(async () => {
      fireEvent.click(sendButton);
    });
    
    // Should not call chat API with empty message
    expect(defaultMockResponse.chat).not.toHaveBeenCalled();
  });

  it('sends message on Enter key (without Shift)', async () => {
    render(<HomePage />);
    
    const input = screen.getByPlaceholderText(/Ask a question/) as HTMLInputElement;
    
    await act(async () => {
      fireEvent.change(input, { target: { value: 'Test query' } });
      fireEvent.keyDown(input, { key: 'Enter', shiftKey: false });
    });
    
    // Should call chat API
    await vi.waitFor(() => {
      expect(defaultMockResponse.chat).toHaveBeenCalled();
    });
  });

  it('does not send message on Shift+Enter', async () => {
    render(<HomePage />);
    
    const input = screen.getByPlaceholderText(/Ask a question/) as HTMLInputElement;
    
    await act(async () => {
      fireEvent.change(input, { target: { value: 'Test query' } });
      fireEvent.keyDown(input, { key: 'Enter', shiftKey: true });
    });
    
    // Should not call chat API
    expect(defaultMockResponse.chat).not.toHaveBeenCalled();
  });

  it('disables send button when loading', async () => {
    let resolveChat: (value: any) => void;
    const mockChat = vi.fn().mockImplementation(() => (
      new Promise<{ data: any }>(resolve => {
        resolveChat = resolve;
      })
    ));
    
    mockUseApi.mockReturnValue({
      ...defaultMockResponse,
      chat: mockChat
    });
    
    render(<HomePage />);
    
    const input = screen.getByPlaceholderText(/Ask a question/) as HTMLInputElement;
    const sendButton = screen.getByText('Send');
    
    // Initially button should be disabled (empty input)
    expect(sendButton).toBeDisabled();
    
    await act(async () => {
      fireEvent.change(input, { target: { value: 'Test query' } });
    });
    
    // Button should be enabled after entering text
    expect(sendButton).not.toBeDisabled();
    
    await act(async () => {
      fireEvent.keyDown(input, { key: 'Enter', shiftKey: false });
    });
    
    // Button should be disabled while loading - use waitFor because state update is async
    await vi.waitFor(() => {
      expect(sendButton).toBeDisabled();
    });
    
    // Resolve the promise
    await act(async () => {
      resolveChat!({ data: {
        message: 'Response',
        citations: [],
        matched_objects: [],
        graph_data: { nodes: [], edges: [] },
        trace: []
      } });
    });
    
    // Wait for the finally block to run and re-enable the button
    await vi.waitFor(() => {
      expect(sendButton).not.toBeDisabled();
    }, { timeout: 1000 });
  });

  it('displays assistant messages after chat', async () => {
    render(<HomePage />);
    
    const input = screen.getByPlaceholderText(/Ask a question/) as HTMLInputElement;
    
    await act(async () => {
      fireEvent.change(input, { target: { value: 'Test query' } });
      fireEvent.keyDown(input, { key: 'Enter', shiftKey: false });
    });
    
    await vi.waitFor(() => {
      expect(screen.getByText('Assistant')).toBeInTheDocument();
      expect(screen.getByText('Test response')).toBeInTheDocument();
    });
  });

  it('displays user messages', async () => {
    render(<HomePage />);
    
    const input = screen.getByPlaceholderText(/Ask a question/) as HTMLInputElement;
    
    await act(async () => {
      fireEvent.change(input, { target: { value: 'Test query' } });
      fireEvent.keyDown(input, { key: 'Enter', shiftKey: false });
    });
    
    await vi.waitFor(() => {
      expect(screen.getByText('You')).toBeInTheDocument();
      expect(screen.getByText('Test query')).toBeInTheDocument();
    });
  });

  it('clears input after sending', async () => {
    render(<HomePage />);
    
    const input = screen.getByPlaceholderText(/Ask a question/) as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'Test query' } });
    expect(input.value).toBe('Test query');
    
    await act(async () => {
      fireEvent.keyDown(input, { key: 'Enter', shiftKey: false });
    });
    
    await vi.waitFor(() => {
      expect(input.value).toBe('');
    });
  });

  it('renders markdown content correctly', async () => {
    mockUseApi.mockReturnValue({
      ...defaultMockResponse,
      chat: vi.fn().mockResolvedValue({ data: {
        message: '# Heading\n\nThis is **bold** text',
        citations: [],
        matched_objects: [],
        graph_data: { nodes: [], edges: [] },
        trace: []
      } })
    });
    
    render(<HomePage />);
    
    const input = screen.getByPlaceholderText(/Ask a question/) as HTMLInputElement;
    
    await act(async () => {
      fireEvent.change(input, { target: { value: 'Test' } });
      fireEvent.keyDown(input, { key: 'Enter', shiftKey: false });
    });
    
    await vi.waitFor(() => {
      // First check that assistant message appears at all
      expect(screen.getByText('Assistant')).toBeInTheDocument();
    });
    
    // Check for heading
    expect(screen.getByText('Heading')).toBeInTheDocument();
    
    // Check that markdown content is rendered (content is in the assistant message)
    const assistantMessage = screen.getByText('Assistant').parentElement;
    expect(assistantMessage?.textContent).toContain('This is');
    expect(assistantMessage?.textContent).toContain('bold');
    expect(assistantMessage?.textContent).toContain('text');
  });

  it('displays citations when present', async () => {
    mockUseApi.mockReturnValue({
      ...defaultMockResponse,
      chat: vi.fn().mockResolvedValue({ data: {
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
      } })
    });
    
    render(<HomePage />);
    
    const input = screen.getByPlaceholderText(/Ask a question/) as HTMLInputElement;
    
    await act(async () => {
      fireEvent.change(input, { target: { value: 'Test' } });
      fireEvent.keyDown(input, { key: 'Enter', shiftKey: false });
    });
    
    await vi.waitFor(() => {
      // Check for Sources section
      expect(screen.getByText('Sources:')).toBeInTheDocument();
      // Check for citation object ID
      expect(screen.getByText('SIMG/TEST/001')).toBeInTheDocument();
    });
  });
});
