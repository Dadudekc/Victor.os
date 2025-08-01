'use strict';

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = {
  language: 'cpp',
  init: function init(Prism) {
    Prism.languages.cpp = Prism.languages.extend('c', {
      keyword: /\b(?:alignas|alignof|asm|auto|bool|break|case|catch|char|char16_t|char32_t|class|compl|const|constexpr|const_cast|continue|decltype|default|delete|do|double|dynamic_cast|else|enum|explicit|export|extern|float|for|friend|goto|if|inline|int|int8_t|int16_t|int32_t|int64_t|uint8_t|uint16_t|uint32_t|uint64_t|long|mutable|namespace|new|noexcept|nullptr|operator|private|protected|public|register|reinterpret_cast|return|short|signed|sizeof|static|static_assert|static_cast|struct|switch|template|this|thread_local|throw|try|typedef|typeid|typename|union|unsigned|using|virtual|void|volatile|wchar_t|while)\b/,
      boolean: /\b(?:true|false)\b/,
      operator: /--?|\+\+?|!=?|<{1,2}=?|>{1,2}=?|->|:{1,2}|={1,2}|\^|~|%|&{1,2}|\|\|?|\?|\*|\/|\b(?:and|and_eq|bitand|bitor|not|not_eq|or|or_eq|xor|xor_eq)\b/
    });

    Prism.languages.insertBefore('cpp', 'keyword', {
      'class-name': {
        pattern: /(class\s+)\w+/i,
        lookbehind: true
      }
    });

    Prism.languages.insertBefore('cpp', 'string', {
      'raw-string': {
        pattern: /R"([^()\\ ]{0,16})\([\s\S]*?\)\1"/,
        alias: 'string',
        greedy: true
      }
    });
  }
};