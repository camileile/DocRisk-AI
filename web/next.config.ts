import type { NextConfig } from "next";
import path from "node:path";
const productionAuth = process.env.NEXT_PUBLIC_AUTH_MODE === "clerk";
// O SDK inclui Server Actions. Elas não fazem parte da exportação offline.
const aliases: Record<string, string> = {
  "@docrisk/clerk": productionAuth ? "./lib/clerk-sdk.tsx" : "./lib/clerk-offline.tsx",
  "@docrisk/clerk-server": productionAuth ? "./lib/clerk-server.ts" : "./lib/clerk-server-offline.ts",
};
const config: NextConfig = {
  ...(productionAuth ? {} : { output: "export" as const }), trailingSlash: true,
  turbopack: { resolveAlias: aliases },
  webpack(config) { config.resolve.alias = { ...config.resolve.alias, ...Object.fromEntries(Object.entries(aliases).map(([key, value]) => [key, path.resolve(value)])) }; return config; },
};
export default config;
