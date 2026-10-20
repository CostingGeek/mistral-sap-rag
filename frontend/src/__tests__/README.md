# Frontend Tests

This directory contains Vitest-based tests for the SAP RAG Chat Application frontend.

## Structure

```
frontend/src/
├── __tests__/
│   ├── README.md           # This file
│   ├── setup.ts           # Test setup and global mocks
│   ├── HomePage.test.tsx  # HomePage component tests
│   ├── markdown.test.ts   # Markdown rendering utility tests
│   │
├── hooks/__tests__/
│   └── useApi.test.ts     # API hook tests
│
└── views/__tests__/
    ├── HomePage.test.tsx  # Duplicate reference (same as above)
    └── ObjectPage.test.tsx # ObjectPage component tests
```

## Test Coverage

### Component Tests

#### HomePage (`HomePage.test.tsx`)
- Rendering without errors
- Display of example queries when empty
- Input field and button rendering
- Scope selector options
- Input value updates
- Empty message handling
- Message sending on Enter key
- Shift+Enter for new line
- Loading states and button disabling
- Assistant message display
- User message display
- Input clearing after send
- Markdown content rendering
- Citation display with corpus badges

#### ObjectPage (`ObjectPage.test.tsx`)
- Loading state display
- Error state display
- Not found state display
- Object information rendering
- Section display
- Related objects display
- No related objects message
- Element references display
- No references message
- Back link functionality
- Object IDs with special characters (slashes)

### Hook Tests

#### useApi (`useApi.test.ts`)
- API methods availability
- GET request handling
- POST request with data
- Successful response handling
- Error response handling
- Network error handling
- Non-JSON error responses
- Abort signal passing
- AbortError re-throwing
- Specific API methods:
  - `chat()` - POST /api/chat
  - `getObject()` - GET /api/object/{id}
  - `getObjectGraph()` - GET /api/object/{id}/graph
  - `healthCheck()` - GET /api/health
- Scope parameter handling
- URL encoding for IDs with slashes

### Utility Tests

#### Markdown Rendering (`markdown.test.ts`)
- List indentation fixing:
  - Renumbering numbered lists with gaps
  - Converting source labels to bullets
  - Reindenting bullets under ordered items
- Inline markdown processing:
  - Bold text (`**text**`)
  - Italic text (`*text*`)
  - Inline code (``` `text` ``)
  - Citation marker cleaning
- Header processing (all levels)
- Table parsing:
  - Row parsing
  - Separator row identification
  - Cell extraction
- Code block identification

#### Citation Extraction
- Extraction from text with bracket notation
- Different citation formats
- Multiple citations in text

## Running Tests

### Install dependencies
```bash
# Navigate to frontend directory
cd frontend

# Install npm dependencies (includes vitest)
npm install

# Or install specific test dependencies
npm install --save-dev vitest @testing-library/react @testing-library/jest-dom jsdom
```

### Run all frontend tests
```bash
# Using make
make test-frontend

# Using npm script
npm test

# Using vitest directly
npx vitest

# With coverage
npx vitest --coverage
```

### Run tests in watch mode
```bash
npx vitest watch
```

### Run specific test files
```bash
# Run HomePage tests
npx vitest frontend/src/__tests__/HomePage.test.tsx

# Run ObjectPage tests
npx vitest frontend/src/views/__tests__/ObjectPage.test.tsx

# Run useApi tests
npx vitest frontend/src/hooks/__tests__/useApi.test.ts

# Run markdown tests
npx vitest frontend/src/__tests__/markdown.test.ts
```

### Run with filters
```bash
# Run only tests matching pattern
npx vitest -t "renders"

# Run tests in specific file
npx vitest HomePage.test.tsx

# Run with verbose output
npx vitest -v
```

## Mocking Strategy

### API Hooks
The `useApi` hook is mocked to return predictable responses:

```typescript
vi.mock('../hooks/useApi', () => ({
  useApi: () => ({
    chat: vi.fn().mockResolvedValue({ data: { message: 'Response' } }),
    getObject: vi.fn().mockResolvedValue({ data: mockObject }),
    getObjectGraph: vi.fn().mockResolvedValue({ data: mockGraph })
  })
}));
```

### Global Mocks
- `window.scrollTo` - Mocked for components that scroll
- `ResizeObserver` - Mocked for components that use it
- `fetch` - Mocked for API request tests

### Testing Library
- Uses `@testing-library/react` for component testing
- Uses `@testing-library/jest-dom` for DOM assertions
- Uses `jsdom` for DOM environment

## Key Test Scenarios Covered

### User Interactions
- Input field changes
- Button clicks
- Keyboard events (Enter, Shift+Enter)
- Form submission
- Loading state management
- Error state management

### Data Display
- Message rendering (user and assistant)
- Markdown rendering:
  - Headers
  - Lists (ordered and unordered)
  - Code blocks
  - Tables
  - Inline styles
- Citation display with badges
- Timing information display
- Source links

### Navigation
- Route handling
- Link navigation
- URL parameter handling
- Object IDs with special characters

### API Integration
- Request/response handling
- Error handling
- Loading states
- Abort signal handling
- Different HTTP methods

### Component States
- Loading states
- Error states
- Empty states
- Success states
- Transition between states

## Adding New Tests

1. Create a new test file in the appropriate `__tests__` directory
2. Import Vitest and Testing Library utilities
3. Mock dependencies (API hooks, external modules)
4. Use `describe` and `it` for test organization
5. Use `render` to mount components
6. Use `screen` for queries
7. Use `fireEvent` for user interactions
8. Use `waitFor` for async operations

### Example Component Test

```typescript
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import MyComponent from '../MyComponent';

// Mock dependencies
vi.mock('../hooks/useSomeHook', () => ({
  useSomeHook: () => ({ data: 'test' })
}));

describe('MyComponent', () => {
  it('renders correctly', () => {
    render(<MyComponent />);
    expect(screen.getByText(/Test/)).toBeInTheDocument();
  });

  it('handles click events', async () => {
    render(<MyComponent />);
    const button = screen.getByRole('button');
    fireEvent.click(button);
    
    await waitFor(() => {
      expect(screen.getByText(/Clicked/)).toBeInTheDocument();
    });
  });
});
```

## Best Practices

- **Isolate tests**: Each test should be independent
- **Mock all external dependencies**: API calls, hooks, context
- **Test user interactions**: Click, type, keyboard events
- **Test all states**: Loading, error, empty, success
- **Use async/await**: For async operations
- **Clean up mocks**: Clear mocks between tests
- **Use descriptive names**: Test names should describe the behavior
- **Test edge cases**: Empty data, errors, validation failures
- **Avoid implementation details**: Test behavior, not implementation

## Current Limitations

The frontend tests currently require Vitest to be installed. The package.json should be updated to include:

```json
{
  "devDependencies": {
    "vitest": "^1.0.0",
    "@testing-library/react": "^14.0.0",
    "@testing-library/jest-dom": "^6.0.0",
    "jsdom": "^23.0.0",
    "@types/jsdom": "^21.0.0"
  },
  "scripts": {
    "test": "vitest",
    "test:watch": "vitest watch",
    "test:coverage": "vitest --coverage"
  }
}
```

## Test Quality Metrics

### Coverage Goals
- **Components**: >80% coverage
- **Hooks**: >80% coverage
- **Utilities**: >90% coverage
- **Edge cases**: All critical paths covered

### Performance
- Tests should run quickly (< 1 second per test)
- Use mocks to avoid real API calls
- Parallelize independent tests

### Maintainability
- Keep tests up to date with code changes
- Update tests when behavior changes
- Remove tests for removed features
- Add tests for new features
