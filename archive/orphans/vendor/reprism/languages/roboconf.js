'use strict';

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = {
  language: 'roboconf',
  init: function init(Prism) {
    Prism.languages.roboconf = {
      comment: /#.*/,
      keyword: {
        pattern: /(^|\s)(?:(?:facet|instance of)(?=[ \t]+[\w-]+[ \t]*\{)|(?:external|import)\b)/,
        lookbehind: true
      },
      component: {
        pattern: /[\w-]+(?=[ \t]*\{)/,
        alias: 'variable'
      },
      property: /[\w.-]+(?=[ \t]*:)/,
      value: {
        pattern: /(=[ \t]*)[^,;]+/,
        lookbehind: true,
        alias: 'attr-value'
      },
      optional: {
        pattern: /\(optional\)/,
        alias: 'builtin'
      },
      wildcard: {
        pattern: /(\.)\*/,
        lookbehind: true,
        alias: 'operator'
      },
      punctuation: /[{},.;:=]/
    };
  }
};