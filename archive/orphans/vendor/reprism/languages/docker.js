'use strict';

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = {
  language: 'docker',
  init: function init(Prism) {
    Prism.languages.docker = {
      keyword: {
        pattern: /(^\s*)(?:ADD|ARG|CMD|COPY|ENTRYPOINT|ENV|EXPOSE|FROM|HEALTHCHECK|LABEL|MAINTAINER|ONBUILD|RUN|SHELL|STOPSIGNAL|USER|VOLUME|WORKDIR)(?=\s)/im,
        lookbehind: true
      },
      string: /("|')(?:(?!\1)[^\\\r\n]|\\(?:\r\n|[\s\S]))*\1/,
      comment: /#.*/,
      punctuation: /---|\.\.\.|[:[\]{}\-,|>?]/
    };

    Prism.languages.dockerfile = Prism.languages.docker;
  }
};