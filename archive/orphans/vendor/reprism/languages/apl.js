'use strict';

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = {
  language: 'apl',
  init: function init(Prism) {
    Prism.languages.apl = {
      comment: /(?:⍝|#[! ]).*$/m,
      string: {
        pattern: /'(?:[^'\r\n]|'')*'/,
        greedy: true
      },
      number: /¯?(?:\d*\.?\d+(?:e[+¯]?\d+)?|¯|∞)(?:j¯?(?:\d*\.?\d+(?:e[+¯]?\d+)?|¯|∞))?/i,
      statement: /:[A-Z][a-z][A-Za-z]*\b/,
      'system-function': {
        pattern: /⎕[A-Z]+/i,
        alias: 'function'
      },
      constant: /[⍬⌾#⎕⍞]/,
      function: /[-+×÷⌈⌊∣|⍳⍸?*⍟○!⌹<≤=>≥≠≡≢∊⍷∪∩~∨∧⍱⍲⍴,⍪⌽⊖⍉↑↓⊂⊃⊆⊇⌷⍋⍒⊤⊥⍕⍎⊣⊢⍁⍂≈⍯↗¤→]/,
      'monadic-operator': {
        pattern: /[\\\/⌿⍀¨⍨⌶&∥]/,
        alias: 'operator'
      },
      'dyadic-operator': {
        pattern: /[.⍣⍠⍤∘⌸@⌺]/,
        alias: 'operator'
      },
      assignment: {
        pattern: /←/,
        alias: 'keyword'
      },
      punctuation: /[\[;\]()◇⋄]/,
      dfn: {
        pattern: /[{}⍺⍵⍶⍹∇⍫:]/,
        alias: 'builtin'
      }
    };
  }
};