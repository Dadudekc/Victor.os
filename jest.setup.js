require('@testing-library/jest-dom');

// Mock window properties
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(),
    removeListener: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Mock WebSocket
global.WebSocket = class MockWebSocket {
  constructor() {
    this.onmessage = null;
    this.onerror = null;
    this.onopen = null;
    this.send = jest.fn();
    this.close = jest.fn();
  }
};

// Mock URL.createObjectURL and URL.revokeObjectURL
global.URL.createObjectURL = jest.fn(() => 'mock-url');
global.URL.revokeObjectURL = jest.fn();

// Mock document.createElement
document.createElement = jest.fn(() => ({
  href: '',
  download: '',
  click: jest.fn(),
  appendChild: jest.fn(),
  removeChild: jest.fn(),
}));

// Mock document.body methods
document.body.appendChild = jest.fn();
document.body.removeChild = jest.fn();

// Mock ResizeObserver
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// Mock style properties for React 18+
const styleProperties = [
  'WebkitAppearance',
  'WebkitAnimation',
  'WebkitTransition',
  'WebkitTransform',
  'WebkitAnimationName',
  'animation',
  'transition',
  'transform'
];

// Create a style object with all required properties
const mockStyle = {};
styleProperties.forEach(prop => {
  mockStyle[prop] = '';
});

// Mock getComputedStyle
window.getComputedStyle = jest.fn(() => mockStyle);

// Ensure documentElement has style
if (!window.document.documentElement.style) {
  window.document.documentElement.style = mockStyle;
}

// Add style properties to HTMLElement prototype
Object.defineProperty(HTMLElement.prototype, 'style', {
  get() {
    return mockStyle;
  }
}); 