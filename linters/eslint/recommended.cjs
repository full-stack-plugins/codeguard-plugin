// codestyle-check: ESLint 推荐配置（TypeScript + JavaScript）
// 使用方法：拷贝为项目根的 eslint.config.js（flat config）或 .eslintrc.cjs

/** @type {import("eslint").Linter.Config[]} */
module.exports = [
    {
        languageOptions: {
            ecmaVersion: "latest",
            sourceType: "module",
            globals: {
                // Node.js / Browser 常用全局
                console: "readonly",
                process: "readonly",
                globalThis: "readonly",
            },
        },
        rules: {
            // 通用最佳实践
            "no-unused-vars": ["error", { argsIgnorePattern: "^_", varsIgnorePattern: "^_" }],
            "no-console": ["warn", { allow: ["warn", "error", "info"] }],
            "no-undef": "error",
            "no-unreachable": "error",
            "no-var": "error",
            "prefer-const": "error",
            eqeqeq: ["error", "always", { null: "ignore" }],
            "no-implicit-coercion": ["warn", { allow: ["!!"] }],
            "no-magic-numbers": "off", // 业务代码中常见
            "max-lines-per-function": ["warn", { max: 200, skipBlankLines: true, skipComments: true }],
            complexity: ["warn", { max: 15 }],
        },
    },
    {
        files: ["**/*.test.{ts,tsx,js,jsx}"],
        rules: {
            "no-magic-numbers": "off",
            "max-lines-per-function": "off",
        },
    },
];
