import '@testing-library/jest-dom/vitest';

// jsdom doesn't implement these - components that call them (Drawer/Modal
// focus handling, TranscriptDrawer's scroll-to-cited, reduced-motion checks)
// would otherwise throw in tests.
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => {};
}

if (!window.matchMedia) {
  window.matchMedia = (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }) as unknown as MediaQueryList;
}
