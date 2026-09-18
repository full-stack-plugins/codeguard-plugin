# css 生态接入

1. 拷贝 `stylelint.config.js` 到项目根（`type: module` 项目改名为 `stylelint.config.cjs`）
2. 拷贝 `.stylelintignore` 到项目根（config.ignoreFiles 在 subprocess 直调形态不可靠，
   原生 ignore 文件在任何调用形态都生效）
3. `npm install --save-dev stylelint stylelint-config-standard`
4. `npx stylelint "**/*.css"` 验证
