module.exports = {
  env: {
    browser: true,
    es2021: true,
    jest: true, // If you are using Jest for testing
  },
  extends: [
    'eslint:recommended',
    'plugin:react/recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:react-hooks/recommended', // For React Hooks rules
    // Consider adding Prettier here if you want ESLint to not conflict with Prettier
    // 'plugin:prettier/recommended', // Make sure to install eslint-plugin-prettier and eslint-config-prettier
  ],
  parser: '@typescript-eslint/parser',
  parserOptions: {
    ecmaFeatures: {
      jsx: true,
    },
    ecmaVersion: 'latest',
    sourceType: 'module',
  },
  plugins: [
    'react',
    '@typescript-eslint',
    // 'prettier' // If using eslint-plugin-prettier
  ],
  settings: {
    react: {
      version: 'detect', // Automatically detects the React version
    },
  },
  rules: {
    'react/react-in-jsx-scope': 'off', // Not needed for React 17+
    '@typescript-eslint/explicit-function-return-type': 'off', // Optional, can be 'warn' or 'error'
    // Add any specific rule overrides here
    // e.g. 'prettier/prettier': ['error', {}, { usePrettierrc: true }] // if using eslint-plugin-prettier
  },
  ignorePatterns: ['node_modules/', 'build/', 'dist/', '.*.js'], // Ignore generated files and dotfiles at root of frontend
}; 