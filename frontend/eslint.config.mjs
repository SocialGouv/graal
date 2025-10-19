import { FlatCompat } from '@eslint/eslintrc'
import js from '@eslint/js'
import tsParser from '@typescript-eslint/parser'
import prettierConfig from 'eslint-config-prettier'
import prettierPlugin from 'eslint-plugin-prettier'
import { defineConfig } from 'eslint/config'
import globals from 'globals'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const compat = new FlatCompat({
  baseDirectory: __dirname,
  recommendedConfig: js.configs.recommended,
  allConfig: js.configs.all
})

// Load Prettier config from src/.prettierrc
const prettierrcPath = path.join(__dirname, 'src', '.prettierrc')
const prettierOptions = JSON.parse(fs.readFileSync(prettierrcPath, 'utf-8'))

export default defineConfig([
  {
    extends: compat.extends(
      'eslint:recommended',
      'plugin:@typescript-eslint/recommended'
    ),

    plugins: {
      prettier: prettierPlugin
    },

    languageOptions: {
      globals: {
        ...globals.node
      },

      parser: tsParser,
      ecmaVersion: 'latest',
      sourceType: 'module'
    },

    rules: {
      ...prettierConfig.rules,
      '@typescript-eslint/no-unused-vars': [
        'error',
        {
          argsIgnorePattern: '^_'
        }
      ],
      '@typescript-eslint/no-explicit-any': 'warn',
      'prettier/prettier': ['error', prettierOptions]
    }
  }
])
