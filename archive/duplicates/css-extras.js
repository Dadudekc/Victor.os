'use strict';

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = {
  language: 'css-extras',
  init: function init(Prism) {
    Prism.languages.css.selector = {
      pattern: /[^{}\s][^{}]*(?=\s*\{)/,
      inside: {
        'pseudo-element': /:(?:after|before|first-letter|first-line|selection)|::[-\w]+/,
        'pseudo-class': /:[-\w]+(?:\(.*\))?/,
        class: /\.[-:.\w]+/,
        id: /#[-:.\w]+/,
        attribute: /\[[^\]]+\]/
      }
    };

    Prism.languages.insertBefore('css', 'function', {
      hexcode: /#[\da-f]{3,8}/i,
      entity: /\\[\da-f]{1,8}/i,
      number: /[\d%.]+/
    });
  }
};