// Polyfill for getComputedStyle and style properties to fix React 18+ test errors
if (!window.getComputedStyle) {
  window.getComputedStyle = function() {
    return {
      getPropertyValue: () => ''
    };
  };
}

if (!window.document.documentElement.style) {
  window.document.documentElement.style = {};
}

['WebkitAppearance', 'WebkitAnimation', 'WebkitTransition', 'WebkitTransform', 'WebkitAnimationName'].forEach(prop => {
  if (!(prop in window.document.documentElement.style)) {
    window.document.documentElement.style[prop] = '';
  }
}); 