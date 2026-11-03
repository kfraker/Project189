import js from "@eslint/js";
import globals from "globals";

// Page code is plain browser scripts, not modules. shell.js declares helpers at the top
// level on purpose so the page scripts and router.js, loaded after it, can call them.
const SHELL_HELPERS = [
  "fmtLbs",
  "getTodayISO",
  "isoDate",
  "daysAgoISO",
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
      // toISOString() converts to UTC, so as a calendar date it's a day off east or west
      // of UTC (it froze the Weigh-ins table in Europe). Use isoDate() from shell.js.
      "no-restricted-syntax": [
        "error",
        {
          selector: "CallExpression[callee.property.name='toISOString']",
          message: "toISOString() gives the UTC date, not the visitor's. Use isoDate() from shell.js.",
        },
      ],
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
