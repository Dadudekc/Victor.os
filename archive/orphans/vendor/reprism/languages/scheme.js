'use strict';

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = {
  language: 'scheme',
  init: function init(Prism) {
    Prism.languages.scheme = {
      comment: /;.*/,
      string: {
        pattern: /"(?:[^"\\\r\n]|\\.)*"|'[^('\s]*/,
        greedy: true
      },
      keyword: {
        pattern: /(\()(?:define(?:-syntax|-library|-values)?|(?:case-)?lambda|let(?:\*|rec)?(?:-values)?|else|if|cond|begin|delay(?:-force)?|parameterize|guard|set!|(?:quasi-)?quote|syntax-rules)/,
        lookbehind: true
      },
      builtin: {
        pattern: /(\()(?:(?:cons|car|cdr|list|call-with-current-continuation|call\/cc|append|abs|apply|eval)\b|null\?|pair\?|boolean\?|eof-object\?|char\?|procedure\?|number\?|port\?|string\?|vector\?|symbol\?|bytevector\?)/,
        lookbehind: true
      },
      number: {
        pattern: /(\s|[()])[-+]?\d*\.?\d+(?:\s*[-+]\s*\d*\.?\d+i)?\b/,
        lookbehind: true
      },
      boolean: /#[tf]/,
      operator: {
        pattern: /(\()(?:[-+*%\/]|[<>]=?|=>?)/,
        lookbehind: true
      },
      function: {
        pattern: /(\()[^\s()]*(?=\s)/,
        lookbehind: true
      },
      punctuation: /[()]/
    };
  }
};