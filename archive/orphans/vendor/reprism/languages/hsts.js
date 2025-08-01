'use strict';

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = {
  language: 'hsts',
  init: function init(Prism) {
    /**
     * Original by Scott Helme.
     *
     * Reference: https://scotthelme.co.uk/hsts-cheat-sheet/
     */

    Prism.languages.hsts = {
      directive: {
        pattern: /\b(?:max-age=|includeSubDomains|preload)/,
        alias: 'keyword'
      },
      safe: {
        pattern: /\d{8,}/,
        alias: 'selector'
      },
      unsafe: {
        pattern: /\d{0,7}/,
        alias: 'function'
      }
    };
  }
};