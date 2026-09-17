// codestyle-check (codeguard): stylelint 推荐配置（CSS/SCSS/LESS）
// 使用方法：拷贝到项目根 stylelint.config.js：
//   npm install --save-dev stylelint stylelint-config-standard
//   npx stylelint "**/*.css"
//   npx stylelint "**/*.css" --fix

/** @type {import('stylelint').Config} */
module.exports = {
    extends: ["stylelint-config-standard"],
    rules: {
        "indentation": 2,
        "max-line-length": 120,
        "color-hex-length": "short",
        "declaration-block-no-duplicate-properties": true,
        "no-descending-specificity": null,   // 组件化样式常触发误报
        "selector-class-pattern": null       // 交给团队 BEM/模块化约定
    },
    ignoreFiles: ["dist/**", "node_modules/**", "build/**"]
};
