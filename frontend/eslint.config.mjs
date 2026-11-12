import coreWebVitals from "eslint-config-next/core-web-vitals";
import typescript from "eslint-config-next/typescript";

// docs/process/coding-standards.md §2 and §4: an UPPER_CASE constant lives in a
// constants.ts, never in a component, a page, a hook or a function body. Next.js
// route handlers keep their names because the framework reads them there.
const CONSTANT = "[A-Z][A-Z0-9_]+";
const ROUTE_HANDLERS = "GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS";

const constantsLiveInConstantsFiles = {
  files: ["app/**/*.{ts,tsx}", "components/**/*.{ts,tsx}", "lib/**/*.{ts,tsx}"],
  ignores: ["**/constants.ts"],
  rules: {
    "no-restricted-syntax": [
      "error",
      {
        selector: `VariableDeclarator[id.name=/^(?!(${ROUTE_HANDLERS})$)${CONSTANT}$/]`,
        message:
          "Constants live in lib/constants.ts or lib/<feature>/constants.ts (docs/process/coding-standards.md).",
      },
    ],
  },
};

const config = [
  { ignores: [".next/**", "node_modules/**"] },
  ...coreWebVitals,
  ...typescript,
  constantsLiveInConstantsFiles,
];

export default config;
