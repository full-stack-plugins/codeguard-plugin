// codeguard: stylelint 推荐配置（CSS/SCSS/LESS）
// 使用方法：拷贝到项目根 stylelint.config.cjs：
//   npm install --save-dev stylelint stylelint-config-standard
//   npx stylelint "**/*.css"
//   npx stylelint "**/*.css" --fix
// 注意：package.json "type": "module" 的项目请用 .cjs 后缀（CommonJS 配置）。
// stylelint 16 已移除 indentation / max-line-length 规则，勿再加回。

/** @type {import('stylelint').Config} */
module.exports = {
    extends: ["stylelint-config-standard"],
    rules: {
        "color-hex-length": "short",
        "declaration-block-no-duplicate-properties": true,
        "no-descending-specificity": null,   // 组件化样式常触发误报
        "selector-class-pattern": null       // 交给团队 BEM/模块化约定
    },
    ignoreFiles: ["dist/**", "node_modules/**", "build/**", "target/**", "docs/**"]
};
