import { spawnSync } from "node:child_process";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { fileURLToPath } from "node:url";
import path from "node:path";

const ccusageVersion = "20.0.20";
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const outputPath = path.join(root, "static", "usage.json");
const claudeConfigDir = process.env.CLAUDE_CONFIG_DIR ?? path.join(homedir(), ".claude");
const claudeStatsPath = path.join(claudeConfigDir, "stats-cache.json");

const result = spawnSync(
  "pnpm",
  ["dlx", `ccusage@${ccusageVersion}`, "daily", "--json", "--breakdown"],
  {
    cwd: root,
    encoding: "utf8",
    maxBuffer: 64 * 1024 * 1024,
  },
);

if (result.error) {
  throw result.error;
}

if (result.status !== 0) {
  process.stderr.write(result.stderr);
  process.exit(result.status ?? 1);
}

let report;
try {
  report = JSON.parse(result.stdout);
} catch (error) {
  process.stderr.write(result.stderr);
  throw new Error(`ccusage returned invalid JSON: ${error.message}`);
}

const number = (value) => (Number.isFinite(Number(value)) ? Number(value) : 0);
const tokenTotal = (value) =>
  number(value.totalTokens) ||
  number(value.inputTokens) +
    number(value.outputTokens) +
    number(value.cacheCreationTokens ?? value.cacheCreationInputTokens) +
    number(value.cacheReadTokens ?? value.cacheReadInputTokens);

const normalizeModels = (row) => {
  if (Array.isArray(row.modelBreakdowns)) {
    return row.modelBreakdowns.map((model) => ({
      name: model.modelName,
      inputTokens: number(model.inputTokens),
      outputTokens: number(model.outputTokens),
      cacheCreationTokens: number(model.cacheCreationTokens),
      cacheReadTokens: number(model.cacheReadTokens),
      totalTokens: tokenTotal(model),
      unclassifiedTokens: 0,
      estimatedCostUsd: number(model.cost ?? model.costUSD),
    }));
  }

  return Object.entries(row.breakdown ?? {}).map(([name, model]) => ({
    name,
    inputTokens: number(model.inputTokens),
    outputTokens: number(model.outputTokens),
    cacheCreationTokens: number(model.cacheCreationTokens),
    cacheReadTokens: number(model.cacheReadTokens),
    totalTokens: tokenTotal(model),
    unclassifiedTokens: 0,
    estimatedCostUsd: number(model.cost ?? model.costUSD),
  }));
};

const sourceDays = report.daily ?? report.data ?? [];
const ccusageDays = sourceDays
  .map((row) => ({
    date: row.period ?? row.date,
    agents: row.metadata?.agents ?? (row.agent && row.agent !== "all" ? [row.agent] : []),
    inputTokens: number(row.inputTokens),
    outputTokens: number(row.outputTokens),
    cacheCreationTokens: number(row.cacheCreationTokens),
    cacheReadTokens: number(row.cacheReadTokens),
    totalTokens: number(row.totalTokens),
    unclassifiedTokens: 0,
    estimatedCostUsd: number(row.totalCost ?? row.costUSD),
    models: normalizeModels(row),
  }))
  .filter((row) => /^\d{4}-\d{2}-\d{2}$/.test(row.date))
  .sort((left, right) => left.date.localeCompare(right.date));

const loadClaudeStats = () => {
  if (!existsSync(claudeStatsPath)) {
    console.warn(`Claude stats cache not found at ${claudeStatsPath}`);
    return null;
  }

  return JSON.parse(readFileSync(claudeStatsPath, "utf8"));
};

const claudeStats = loadClaudeStats();
const claudeActivity = new Map((claudeStats?.dailyActivity ?? []).map((day) => [day.date, day]));
const claudeDailyModels = new Map(
  (claudeStats?.dailyModelTokens ?? []).map((day) => [day.date, day.tokensByModel]),
);
const allDates = new Set([
  ...ccusageDays.map((day) => day.date),
  ...claudeActivity.keys(),
  ...claudeDailyModels.keys(),
]);
const ccusageByDate = new Map(ccusageDays.map((day) => [day.date, day]));

const mergeClaudeModels = (models, cachedModels = {}) => {
  const merged = new Map(models.map((model) => [model.name, model]));

  Object.entries(cachedModels).forEach(([name, cachedTokens]) => {
    const current = merged.get(name) ?? {
      name,
      inputTokens: 0,
      outputTokens: 0,
      cacheCreationTokens: 0,
      cacheReadTokens: 0,
      totalTokens: 0,
      unclassifiedTokens: 0,
      estimatedCostUsd: 0,
    };
    const totalTokens = Math.max(current.totalTokens, number(cachedTokens));
    merged.set(name, {
      ...current,
      totalTokens,
      unclassifiedTokens: Math.max(0, totalTokens - tokenTotal(current)),
    });
  });

  return [...merged.values()].sort((left, right) => right.totalTokens - left.totalTokens);
};

const days = [...allDates].sort().map((date) => {
  const current = ccusageByDate.get(date) ?? {
    date,
    agents: [],
    inputTokens: 0,
    outputTokens: 0,
    cacheCreationTokens: 0,
    cacheReadTokens: 0,
    totalTokens: 0,
    unclassifiedTokens: 0,
    estimatedCostUsd: 0,
    models: [],
  };
  const activity = claudeActivity.get(date);
  const cachedModels = claudeDailyModels.get(date);
  const models = mergeClaudeModels(current.models, cachedModels);
  const totalTokens = models.reduce((total, model) => total + model.totalTokens, 0);
  const classifiedTokens =
    current.inputTokens +
    current.outputTokens +
    current.cacheCreationTokens +
    current.cacheReadTokens;

  return {
    ...current,
    agents: [
      ...new Set([...current.agents, ...(activity || cachedModels ? ["claude"] : [])]),
    ].sort(),
    activity: activity
      ? {
          messages: number(activity.messageCount),
          sessions: number(activity.sessionCount),
          toolCalls: number(activity.toolCallCount),
        }
      : null,
    totalTokens,
    unclassifiedTokens: Math.max(0, totalTokens - classifiedTokens),
    models,
  };
});

const sum = (key) => days.reduce((total, day) => total + day[key], 0);
const agents = [...new Set(days.flatMap((day) => day.agents))].sort();
const claudeModels = Object.entries(claudeStats?.modelUsage ?? {})
  .map(([name, model]) => ({
    name,
    inputTokens: number(model.inputTokens),
    outputTokens: number(model.outputTokens),
    cacheCreationTokens: number(model.cacheCreationInputTokens),
    cacheReadTokens: number(model.cacheReadInputTokens),
    totalTokens: tokenTotal(model),
  }))
  .sort((left, right) => right.totalTokens - left.totalTokens);

const output = {
  generatedAt: new Date().toISOString(),
  sources: [
    `ccusage@${ccusageVersion} daily --json --breakdown`,
    ...(claudeStats ? [`Claude stats cache v${claudeStats.version}`] : []),
  ],
  totals: {
    activeDays: days.filter((day) => day.totalTokens > 0 || day.activity?.messages > 0).length,
    agents,
    inputTokens: sum("inputTokens"),
    outputTokens: sum("outputTokens"),
    cacheCreationTokens: sum("cacheCreationTokens"),
    cacheReadTokens: sum("cacheReadTokens"),
    unclassifiedTokens: sum("unclassifiedTokens"),
    totalTokens: sum("totalTokens"),
    estimatedCostUsd: sum("estimatedCostUsd"),
  },
  claude: claudeStats
    ? {
        cacheVersion: number(claudeStats.version),
        firstSessionAt: claudeStats.firstSessionDate,
        lastComputedDate: claudeStats.lastComputedDate,
        totalSessions: number(claudeStats.totalSessions),
        totalMessages: number(claudeStats.totalMessages),
        models: claudeModels,
      }
    : null,
  days,
};

writeFileSync(outputPath, `${JSON.stringify(output, null, 2)}\n`);
console.log(`Wrote ${days.length} days to ${path.relative(root, outputPath)}`);
