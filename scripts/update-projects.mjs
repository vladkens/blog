import { writeFile } from "node:fs/promises";

const repos = [
  ["vladkens/twscrape", "Python library for scraping X"],
  ["vladkens/macmon", "MacOS CLI tool for performance monitoring"],
  ["vladkens/ghstats", "Self-hosted GitHub stats for your repos"],
  ["vladkens/apigen-ts", "Generate TypeScript API clients from OpenAPI"],
  ["vladkens/ecloop", "secp256k1 elliptic curve brute-forcing"],
  ["vladkens/ogp", "Open Graph image generator as a service"],
  ["vladkens/timewiz", "Time zone viewer & meeting planner"],
  ["vladkens/badges", "Nice badges for your projects"],
];

const fetchRepo = async (repo) => {
  const response = await fetch(`https://api.github.com/repos/${repo}`);
  if (!response.ok) {
    throw new Error(
      `GitHub API request failed for ${repo}: ${response.status} ${response.statusText}`,
    );
  }

  return response.json();
};

const formatItems = (items) => {
  const raw = JSON.stringify(items, null, 2);
  return raw.replace(/\[\n\s+"/g, '["').replace(/"\n\s+\]/g, '"]') + "\n";
};

try {
  const items = await Promise.all(
    repos.map(async ([repo, descr]) => {
      const data = await fetchRepo(repo);
      return {
        name: repo,
        descr: descr || data.description,
        langs: [data.language],
        stars: data.stargazers_count,
      };
    }),
  );

  items.sort((a, b) => b.stars - a.stars);
  await writeFile("projects.json", formatItems(items));
} catch (error) {
  console.error(error.message);
  process.exit(1);
}
