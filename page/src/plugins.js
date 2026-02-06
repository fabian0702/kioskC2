const plugins = import.meta.glob("./plugins/*.js", { eager: true });

for (const mod of Object.values(plugins)) {
  console.log(`imported plugin: ${mod.default}`);
}