'use strict';

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = {
  language: 'rip',
  init: function init(Prism) {
    Prism.languages.rip = {
      comment: /#.*/,

      keyword: /(?:=>|->)|\b(?:class|if|else|switch|case|return|exit|try|catch|finally|raise)\b/,

      builtin: /@|\bSystem\b/,

      boolean: /\b(?:true|false)\b/,

      date: /\b\d{4}-\d{2}-\d{2}\b/,
      time: /\b\d{2}:\d{2}:\d{2}\b/,
      datetime: /\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\b/,

      character: /\B`[^\s`'",.:;#\/\\()<>\[\]{}]\b/,

      regex: {
        pattern: /(^|[^/])\/(?!\/)(\[.+?]|\\.|[^/\\\r\n])+\/(?=\s*($|[\r\n,.;})]))/,
        lookbehind: true,
        greedy: true
      },

      symbol: /:[^\d\s`'",.:;#\/\\()<>\[\]{}][^\s`'",.:;#\/\\()<>\[\]{}]*/,
      string: {
        pattern: /("|')(?:\\.|(?!\1)[^\\\r\n])*\1/,
        greedy: true
      },
      number: /[+-]?(?:(?:\d+\.\d+)|(?:\d+))/,

      punctuation: /(?:\.{2,3})|[`,.:;=\/\\()<>\[\]{}]/,

      reference: /[^\d\s`'",.:;#\/\\()<>\[\]{}][^\s`'",.:;#\/\\()<>\[\]{}]*/
    };
  }
};