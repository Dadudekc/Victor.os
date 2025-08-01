'use strict';

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = {
  language: 'oz',
  init: function init(Prism) {
    Prism.languages.oz = {
      comment: /\/\*[\s\S]*?\*\/|%.*/,
      string: {
        pattern: /"(?:[^"\\]|\\[\s\S])*"/,
        greedy: true
      },
      atom: {
        pattern: /'(?:[^'\\]|\\[\s\S])*'/,
        greedy: true,
        alias: 'builtin'
      },
      keyword: /[$_]|\[\]|\b(?:at|attr|case|catch|choice|class|cond|declare|define|dis|else(?:case|if)?|end|export|fail|false|feat|finally|from|fun|functor|if|import|in|local|lock|meth|nil|not|of|or|prepare|proc|prop|raise|require|self|skip|then|thread|true|try|unit)\b/,
      function: [/[a-z][A-Za-z\d]*(?=\()/, {
        pattern: /(\{)[A-Z][A-Za-z\d]*/,
        lookbehind: true
      }],
      number: /\b(?:0[bx][\da-f]+|\d+\.?\d*(?:e~?\d+)?\b)|&(?:[^\\]|\\(?:\d{3}|.))/i,
      variable: /\b[A-Z][A-Za-z\d]*|`(?:[^`\\]|\\.)+`/,
      'attr-name': /\w+(?=:)/,
      operator: /:(?:=|::?)|<[-:=]?|=(?:=|<?:?)|>=?:?|\\=:?|!!?|[|#+\-*\/,~^@]|\b(?:andthen|div|mod|orelse)\b/,
      punctuation: /[\[\](){}.:;?]/
    };
  }
};