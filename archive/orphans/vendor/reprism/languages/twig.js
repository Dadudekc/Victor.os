'use strict';

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = {
  language: 'twig',
  init: function init(Prism) {
    Prism.languages.twig = {
      comment: /\{#[\s\S]*?#\}/,
      tag: {
        pattern: /\{\{[\s\S]*?\}\}|\{%[\s\S]*?%\}/,
        inside: {
          ld: {
            pattern: /^(?:\{\{-?|\{%-?\s*\w+)/,
            inside: {
              punctuation: /^(?:\{\{|\{%)-?/,
              keyword: /\w+/
            }
          },
          rd: {
            pattern: /-?(?:%\}|\}\})$/,
            inside: {
              punctuation: /.*/
            }
          },
          string: {
            pattern: /("|')(?:\\.|(?!\1)[^\\\r\n])*\1/,
            inside: {
              punctuation: /^['"]|['"]$/
            }
          },
          keyword: /\b(?:even|if|odd)\b/,
          boolean: /\b(?:true|false|null)\b/,
          number: /\b0x[\dA-Fa-f]+|(?:\b\d+\.?\d*|\B\.\d+)(?:[Ee][-+]?\d+)?/,
          operator: [{
            pattern: /(\s)(?:and|b-and|b-xor|b-or|ends with|in|is|matches|not|or|same as|starts with)(?=\s)/,
            lookbehind: true
          }, /[=<>]=?|!=|\*\*?|\/\/?|\?:?|[-+~%|]/],
          property: /\b[a-zA-Z_]\w*\b/,
          punctuation: /[()\[\]{}:.,]/
        }
      },

      // The rest can be parsed as HTML
      other: {
        // We want non-blank matches
        pattern: /\S(?:[\s\S]*\S)?/,
        inside: Prism.languages.markup
      }
    };
  }
};