'use strict';

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = {
  language: 'icon',
  init: function init(Prism) {
    Prism.languages.icon = {
      comment: /#.*/,
      string: {
        pattern: /(["'])(?:(?!\1)[^\\\r\n_]|\\.|_(?!\1)(?:\r\n|[\s\S]))*\1/,
        greedy: true
      },
      number: /\b(?:\d+r[a-z\d]+|\d+(?:\.\d+)?(?:e[+-]?\d+)?)\b|\.\d+\b/i,
      'builtin-keyword': {
        pattern: /&(?:allocated|ascii|clock|collections|cset|current|date|dateline|digits|dump|e|error(?:number|text|value)?|errout|fail|features|file|host|input|lcase|letters|level|line|main|null|output|phi|pi|pos|progname|random|regions|source|storage|subject|time|trace|ucase|version)\b/,
        alias: 'variable'
      },
      directive: {
        pattern: /\$\w+/,
        alias: 'builtin'
      },
      keyword: /\b(?:break|by|case|create|default|do|else|end|every|fail|global|if|initial|invocable|link|local|next|not|of|procedure|record|repeat|return|static|suspend|then|to|until|while)\b/,
      function: /(?!\d)\w+(?=\s*[({]|\s*!\s*\[)/,
      operator: /[+-]:(?!=)|(?:[\/?@^%&]|\+\+?|--?|==?=?|~==?=?|\*\*?|\|\|\|?|<(?:->?|<?=?)|>>?=?)(?::=)?|:(?:=:?)?|[!.\\|~]/,
      punctuation: /[\[\](){},;]/
    };
  }
};