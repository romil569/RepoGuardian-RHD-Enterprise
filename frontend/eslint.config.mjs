import next from "eslint-config-next";

const eslintConfig = [
  {
    ignores: [".next/**", "node_modules/**", "out/**", "dist/**", "build/**"]
  },
  ...next
];

export default eslintConfig;
