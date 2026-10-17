#!/usr/bin/env node
/**
 * bump-plugin.mjs —— partme 插件发版一条命令。
 *
 * 纪律：任何代码改动（无论大小）都要 bump + 发版，市场端靠版本号感知更新。
 *
 * 用法：
 *   node scripts/bump-plugin.mjs <plugin-id> <major|minor|patch> [--dry-run]
 * 例：
 *   node scripts/bump-plugin.mjs codeguard patch
 *
 * 做的事：
 *   1. catalog.json 该插件 version bump
 *   2. 插件现有清单与可选[project].version同步；Claude plugin/marketplace分别处理，
 *      .codex-plugin 带当日 +codex.日期 后缀，所有漂移在写入前拒绝
 *   3. 重跑 sync-marketplaces.mjs --write 重新生成三平台清单并校验
 *   4. 打印两仓待提交提示
 */
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const root = resolvePluginsRoot();
const [pluginId, level, dryRunFlag] = process.argv.slice(2);
const dryRun = dryRunFlag === "--dry-run";

/**
 * 定位 plugins 市场仓（含 catalog.json 的那个目录）。
 * 本脚本同时存在于 plugins/scripts/（主本）和每个插件仓 scripts/（分发副本），
 * 两种位置都要能找到市场仓：
 *   a) PARTME_PLUGINS_ROOT 环境变量
 *   b) 脚本位于 <plugins>/scripts/ 下（主本）
 *   c) 从脚本位置向上找 <dir>/plugins/catalog.json（插件仓分发副本场景）
 */
function resolvePluginsRoot() {
  if (process.env.PARTME_PLUGINS_ROOT) return path.resolve(process.env.PARTME_PLUGINS_ROOT);
  const scriptDir = path.dirname(fileURLToPath(import.meta.url));
  if (path.basename(scriptDir) === "scripts" && fs.existsSync(path.join(scriptDir, "..", "catalog.json"))) {
    return path.resolve(scriptDir, "..");
  }
  let dir = path.resolve(scriptDir, "..");
  // 优先：插件仓位于 <市场名>-repositories/<插件>/ 下时，市场就是上两级的 <市场名>
  const repoDirName = path.basename(path.dirname(dir));   // …/<市场>-repositories
  if (repoDirName.endsWith("-repositories")) {
    const market = path.join(path.dirname(path.dirname(dir)), repoDirName.replace(/-repositories$/, ""));
    if (fs.existsSync(path.join(market, "catalog.json"))) return market;
  }
  while (dir !== path.parse(dir).root) {
    if (fs.existsSync(path.join(dir, "plugins", "catalog.json"))) return path.join(dir, "plugins");
    const candidates = [];
    try {
      for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
        if (entry.isDirectory() && /-plugins$/.test(entry.name)
            && fs.existsSync(path.join(dir, entry.name, "catalog.json"))) {
          candidates.push(path.join(dir, entry.name));
        }
      }
    } catch { /* 不可读目录跳过 */ }
    if (candidates.length === 1) return candidates[0];
    if (candidates.length > 1) {
      // 歧义目录（如工作区根同时含多个 *-plugins 市场仓）拒绝 first-match：
      // 静默选错市场会把版本写进错误的 catalog。
      throw new Error(
        `发现多个插件市场仓候选，拒绝猜测，请设 PARTME_PLUGINS_ROOT 指定：\n  ${candidates.join("\n  ")}`,
      );
    }
    dir = path.dirname(dir);
  }
  throw new Error("找不到插件市场仓。可设 PARTME_PLUGINS_ROOT 指定。");
}


if (!pluginId || !["major", "minor", "patch"].includes(level)
    || process.argv.slice(2).length > 3 || (dryRunFlag !== undefined && !dryRun)) {
  console.error("用法: node scripts/bump-plugin.mjs <plugin-id> <major|minor|patch> [--dry-run]");
  process.exit(1);
}

const bump = (v) => {
  if (typeof v !== "string" || !/^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/.test(v)) throw new Error(`无法解析版本号: ${v}`);
  const parts = v.split(".").map(Number);
  const index = {major: 0, minor: 1, patch: 2}[level];
  if (parts.some(n => !Number.isSafeInteger(n)) || !Number.isSafeInteger(parts[index] + 1)) throw new Error(`版本号超出安全范围: ${v}`);
  parts[index] += 1;
  for (let i = index + 1; i < parts.length; i++) parts[i] = 0;
  return parts.join(".");
};

const catalogPath = path.join(root, "catalog.json");
const workspace = path.resolve(root, "..", "full-stack-plugins-repositories");
const catalog = JSON.parse(fs.readFileSync(catalogPath, "utf8"));
const plugin = catalog.plugins.find((p) => p.id === pluginId);
if (!plugin) {
  console.error(`catalog.json 里没有插件: ${pluginId}（现有: ${catalog.plugins.map((p) => p.id).join(", ")}）`);
  process.exit(1);
}

const oldVersion = plugin.version;
const newVersion = bump(oldVersion);
const today = new Intl.DateTimeFormat("en-CA", {
  timeZone: "Asia/Shanghai",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
}).format(new Date()).replaceAll("-", "");
const repoDir = path.join(workspace, plugin.localDirectory);


// 所有目标先解析和核对，再写入任何文件；dry-run也必须拒绝漂移。
const writes = new Map();
const checks = [];
const edits = [];
const format = value => `${JSON.stringify(value, null, 2)}\n`;
const parse = file => JSON.parse(fs.readFileSync(file, "utf8"));
function expectVersion(actual, expected, label) {
  if (actual !== expected) throw new Error(`${label}: 版本 ${actual ?? "(未找到)"} 与计划 ${expected} 漂移；拒绝写入，请先对齐已发布版本`);
}
function planJson(rel, readVersion, update, expected = oldVersion, target = newVersion) {
  const file = path.join(repoDir, rel);
  const value = parse(file);
  expectVersion(readVersion(value), expected, rel);
  update(value);
  expectVersion(readVersion(value), target, rel);
  writes.set(file, format(value));
  checks.push(() => expectVersion(readVersion(parse(file)), target, `${rel} 写后回读`));
  edits.push({file, description: `${rel}: ${expected} -> ${target}`});
}
const onePlugin = (value, label) => {
  if (!Array.isArray(value.plugins) || value.plugins.length !== 1 || !value.plugins[0] || typeof value.plugins[0] !== "object") {
    throw new Error(`${label}: repository marketplace must contain exactly one plugin`);
  }
  return value.plugins[0];
};
const plainManifestRels = [".zcode-plugin/plugin.json", "kimi.plugin.json"];
for (const optional of ["plugin.json", ".claude-plugin/plugin.json"]) {
  if (fs.existsSync(path.join(repoDir, optional))) plainManifestRels.push(optional);
}
for (const rel of plainManifestRels) planJson(rel, v => v.version, v => {v.version = newVersion;});

const claudeMarketplace = ".claude-plugin/marketplace.json";
if (fs.existsSync(path.join(repoDir, claudeMarketplace))) {
  planJson(claudeMarketplace, v => onePlugin(v, claudeMarketplace).version,
    v => {onePlugin(v, claudeMarketplace).version = newVersion;});
}
const agents = ".agents/plugins/marketplace.json";
planJson(agents, v => onePlugin(v, agents).version, v => {
  const entry = onePlugin(v, agents);
  if (!entry.source || typeof entry.source !== "object" || !entry.interface || typeof entry.interface !== "object") {
    throw new Error(`${agents}: source/interface object required`);
  }
  entry.version = newVersion;
  entry.description = plugin.description;
  entry.interface.shortDescription = plugin.shortDescription;
  entry.source.ref = `v${newVersion}`;
  entry.icon = `https://cdn.jsdelivr.net/gh/${plugin.repository}@v${newVersion}/${plugin.logo}`;
  entry.interface.logo = entry.icon;
});
const codex = ".codex-plugin/plugin.json";
const codexOld = parse(path.join(repoDir, codex)).version;
const codexPrefix = `${oldVersion}+codex.`;
if (typeof codexOld !== "string" || !(codexOld === oldVersion || (codexOld.startsWith(codexPrefix) && /^\d{8}$/.test(codexOld.slice(codexPrefix.length))))) {
  throw new Error(`${codex}: 版本 ${codexOld} 与 catalog ${oldVersion} 漂移；拒绝写入`);
}
planJson(codex, v => v.version, v => {v.version = `${newVersion}+codex.${today}`;}, codexOld, `${newVersion}+codex.${today}`);

// 只编辑[project]的唯一静态version字符串；保留其他表、引号、注释和换行。
// 扫描字符串状态，不能将多行description里的伪[project]/version当成元数据。
function pythonProjectVersion(text) {
  let offset = 0, project = false, seen = false, seenTable = false, quote = null, depth = 0;
  const versions = [];
  for (const line of text.match(/[^\n]*\n|[^\n]+$/g) ?? []) {
    const eligible = quote === null && depth === 0;
    if (eligible && /^\s*\[/.test(line)) {
      seenTable = true;
      project = /^\s*\[\s*(?:project|"project"|'project')\s*\]\s*(?:#.*)?(?:\r?\n)?$/.test(line);
      if (project && seen) throw new Error("pyproject.toml: duplicate [project] table");
      seen ||= project;
    } else if (eligible && project && /^\s*(?:version|"version"|'version')\s*=/.test(line)) {
      const match = /^(\s*(?:version|"version"|'version')\s*=\s*)(["'])([^"'\r\n]*)\2\s*(?:#.*)?(?:\r?\n)?$/.exec(line);
      if (!match) throw new Error("pyproject.toml: one static project version string required");
      versions.push({value: match[3], start: offset + match[1].length + 1});
    } else if (eligible && !seenTable && /^\s*(?:project\.|project\s*=|"project"\s*=|'project'\s*=)/.test(line)) {
      throw new Error("pyproject.toml: unsupported project table form; explicit [project] version required");
    }
    for (let i = 0; i < line.length; i++) {
      if (quote !== null) {
        if (quote[0] === '"' && line.charCodeAt(i) === 92) { i++; continue; }
        if (line.startsWith(quote, i)) { i += quote.length - 1; quote = null; }
      } else {
        if (line[i] === "#") break;
        if (line[i] === '"' || line[i] === "'") {
          const triple = line[i].repeat(3);
          quote = line.startsWith(triple, i) ? triple : line[i];
          i += quote.length - 1;
        } else if (line[i] === "[" || line[i] === "{") depth++;
        else if (line[i] === "]" || line[i] === "}") depth--;
      }
    }
    if (quote !== null && quote.length === 1) throw new Error("pyproject.toml: malformed single-line string");
    offset += line.length;
  }
  if (quote !== null || depth !== 0) throw new Error("pyproject.toml: unclosed string or collection");
  if (seen && versions.length !== 1) throw new Error("pyproject.toml: exactly one static [project].version required");
  return seen ? versions[0] : null;
}
const pyproject = path.join(repoDir, "pyproject.toml");
if (fs.existsSync(pyproject)) {
  const original = fs.readFileSync(pyproject, "utf8");
  const entry = pythonProjectVersion(original);
  if (entry) {
    expectVersion(entry.value, oldVersion, "pyproject.toml [project].version");
    writes.set(pyproject, original.slice(0, entry.start) + newVersion + original.slice(entry.start + entry.value.length));
    checks.push(() => expectVersion(pythonProjectVersion(fs.readFileSync(pyproject, "utf8"))?.value, newVersion, "pyproject.toml 写后回读"));
    edits.push({file: pyproject, description: `[project].version: ${oldVersion} -> ${newVersion}`});
  }
}

// 保留现有catalog文本布局，同时核对改动恰好是目标插件version，避免误改邻项。
let catalogText = fs.readFileSync(catalogPath, "utf8");
const needle = `"id": "${pluginId}"`;
const index = catalogText.indexOf(needle);
if (index === -1) throw new Error(`catalog.json 中找不到 ${pluginId}`);
const begin = catalogText.indexOf('"version": "', index);
const end = catalogText.indexOf('"', begin + 12);
if (begin === -1 || end === -1) throw new Error("catalog.json: version token unavailable");
catalogText = catalogText.slice(0, begin) + `"version": "${newVersion}"` + catalogText.slice(end + 1);
const expectedCatalog = structuredClone(catalog);
expectedCatalog.plugins.find(p => p.id === pluginId).version = newVersion;
if (JSON.stringify(JSON.parse(catalogText)) !== JSON.stringify(expectedCatalog)) throw new Error("catalog.json: targeted version edit ambiguous; refusing mutation");
writes.set(catalogPath, catalogText);
checks.push(() => expectVersion(parse(catalogPath).plugins.find(p => p.id === pluginId)?.version, newVersion, "catalog.json 写后回读"));
edits.unshift({file: catalogPath, description: `${pluginId}: ${oldVersion} -> ${newVersion}`});

const bumpReadme = text => {
  let next = text.split(`v${oldVersion}`).join(`v${newVersion}`);
  next = next.split(oldVersion).join(newVersion);
  return next.replace(/(\d+\.\d+\.\d+)\+codex\.\d+/g,
    (match, version) => version === newVersion ? `${newVersion}+codex.${today}` : match);
};
for (const name of ["README.md", "README.zh-CN.md"]) {
  const file = path.join(repoDir, name);
  if (fs.existsSync(file)) writes.set(file, bumpReadme(fs.readFileSync(file, "utf8")));
}
console.log(`发版计划: ${pluginId} ${oldVersion} -> ${newVersion}${dryRun ? "（dry-run，不写文件）" : ""}`);
for (const edit of edits) console.log(`  - ${path.relative(workspace, edit.file)}  ${edit.description}`);
if (dryRun) process.exit(0);
for (const [file, text] of writes) fs.writeFileSync(file, text);
for (const check of checks) check();

const pluginFilter = `--plugin=${pluginId}`;
execFileSync(process.execPath, [path.join(root, "scripts/sync-marketplaces.mjs"), "--write", pluginFilter], {stdio: "inherit"});
execFileSync(process.execPath, [path.join(root, "scripts/sync-marketplaces.mjs"), pluginFilter], {stdio: "inherit"});
console.log(`
✅ ${pluginId} ${newVersion} 本地元数据已准备；尚未提交、推送或发布。剩余步骤：
  cd ${root} && git add -A && git commit -m "release: ${pluginId} ${newVersion}" && git push
  cd ${repoDir} && git add -A && git commit -m "release: v${newVersion}" && git push
  ZCode 插件市场刷新后即可看到「可更新」`);
