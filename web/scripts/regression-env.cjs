/* Carrega os módulos TypeScript em contexto isolado, sem backend. */
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ts = require("typescript");
const root = path.resolve(__dirname, "..");
function environment(blocked = false, overrides = {}, modules = {}) {
  const storage = new Map();
  let fetches = 0;
  const context = vm.createContext({
    console, process, Error, SyntaxError, TypeError, URL, URLSearchParams, Headers, FormData, Blob, File, Response, AbortController,
    sessionStorage: {
      getItem(key) { if (blocked) throw Error('blocked'); return storage.get(key) ?? null; },
      setItem(key, value) { if (blocked) throw Error('blocked'); storage.set(key, value); },
      removeItem(key) { if (blocked) throw Error('blocked'); storage.delete(key); },
    },
    fetch: async () => { fetches++; throw Error('unexpected operational fetch'); },
    setTimeout, clearTimeout, window: { setTimeout, clearTimeout },
    ...overrides,
  });
  const cache = new Map();
  function load(file) {
    if (!file.startsWith('.')) return require(file);
    const resolved = path.resolve(root, file);
    if (cache.has(resolved)) return cache.get(resolved).exports;
    const mod = { exports: {} }; cache.set(resolved, mod);
    const source = ts.transpileModule(fs.readFileSync(resolved, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2017, jsx: ts.JsxEmit.ReactJSX } }).outputText;
    const localRequire = (id) => {
      if (id in modules) return modules[id];
      if (id.startsWith('.') || id.startsWith('@/')) {
        let target = id.startsWith('@/') ? path.resolve(root, id.slice(2)) : path.resolve(path.dirname(resolved), id);
        if (!path.extname(target)) target += fs.existsSync(target + '.ts') ? '.ts' : '.tsx';
        return load('./' + path.relative(root, target));
      }
      return require(id);
    };
    vm.runInContext('(function(require,module,exports){' + source + '\n})', context, { filename: resolved })(localRequire, mod, mod.exports);
    return mod.exports;
  }
  return { load, context, storage, fetches: () => fetches };
}

module.exports = { environment };
