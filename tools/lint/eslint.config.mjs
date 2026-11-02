import js from "@eslint/js";
import globals from "globals";

// Page code is plain browser scripts, not modules. shell.js declares helpers at the top
// level on purpose so the page scripts and router.js, loaded after it, can call them.
const SHELL_HELPERS = [
  "fmtLbs",
  "getTodayISO",
  "formatDateDisplay",
  "formatDateShort",
  "modalOpen",
  "modalClose",
  "announce",
  "applyStreakGlow",
];

export default [
  js.configs.recommended,
  {
    languageOptions: {
      ecmaVersion: 2024,
      sourceType: "script",
      globals: { ...globals.browser, Chart: "readonly", registerPage: "readonly", appRouter: "readonly" },
    },
    rules: {
      eqeqeq: ["error", "always", { null: "ignore" }],
      "no-empty": ["error", { allowEmptyCatch: true }],
      "no-implicit-globals": "error",
      "no-unused-vars": ["error", { caughtErrors: "none" }],
    },
  },
  {
    files: ["static/js/shell.js"],
    rules: {
      "no-implicit-globals": "off",
      "no-unused-vars": ["error", { caughtErrors: "none", vars: "local" }],
    },
  },
  {
    files: ["static/js/router.js", "static/js/pages/**/*.js"],
    languageOptions: { globals: Object.fromEntries(SHELL_HELPERS.map((name) => [name, "readonly"])) },
  },
];
