'use strict';

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = {
  language: 'less',
  init: function init(Prism) {
    /* FIXME :
    :extend() is not handled specifically : its highlighting is buggy.
    Mixin usage must be inside a ruleset to be highlighted.
    At-rules (e.g. import) containing interpolations are buggy.
    Detached rulesets are highlighted as at-rules.
    A comment before a mixin usage prevents the latter to be properly highlighted.
    */

    Prism.languages.less = Prism.languages.extend('css', {
      comment: [/\/\*[\s\S]*?\*\//, {
        pattern: /(^|[^\\])\/\/.*/,
        lookbehind: true
      }],
      atrule: {
        pattern: /@[\w-]+?(?:\([^{}]+\)|[^(){};])*?(?=\s*\{)/i,
        inside: {
          punctuation: /[:()]/
        }
      },
      // selectors and mixins are considered the same
      selector: {
        pattern: /(?:@\{[\w-]+\}|[^{};\s@])(?:@\{[\w-]+\}|\([^{}]*\)|[^{};@])*?(?=\s*\{)/,
        inside: {
          // mixin parameters
          variable: /@+[\w-]+/
        }
      },

      property: /(?:@\{[\w-]+\}|[\w-])+(?:\+_?)?(?=\s*:)/i,
      punctuation: /[{}();:,]/,
      operator: /[+\-*\/]/
    });

    // Invert function and punctuation positions
    Prism.languages.insertBefore('less', 'punctuation', {
      function: Prism.languages.less.function
    });

    Prism.languages.insertBefore('less', 'property', {
      variable: [
      // Variable declaration (the colon must be consumed!)
      {
        pattern: /@[\w-]+\s*:/,
        inside: {
          punctuation: /:/
        }
      },

      // Variable usage
      /@@?[\w-]+/],
      'mixin-usage': {
        pattern: /([{;]\s*)[.#](?!\d)[\w-]+.*?(?=[(;])/,
        lookbehind: true,
        alias: 'function'
      }
    });
  }
};