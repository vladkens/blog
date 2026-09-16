(() => {
  const root = document.querySelector(".ai-usage");
  if (!root) return;

  const monthNames = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
  ];
  const colors = [
    [0, 119, 204],
    [238, 119, 51],
    [0, 153, 136],
    [204, 51, 102],
    [187, 187, 187],
    [51, 34, 136],
    [238, 204, 102],
    [68, 170, 153],
    [170, 68, 153],
    [102, 153, 204],
    [153, 153, 51],
    [136, 34, 85],
  ];
  const charts = [];
  let report;
  let period = "daily";

  const modelTokens = (model) =>
    model.totalTokens ??
    model.inputTokens + model.outputTokens + model.cacheCreationTokens + model.cacheReadTokens;

  const compactNumber = (value) =>
    new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 }).format(value);

  const isoDate = (date) => {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  };

  const startOfWeek = (dateString) => {
    const date = new Date(`${dateString}T00:00:00`);
    const offset = date.getDay() === 0 ? -6 : 1 - date.getDay();
    date.setDate(date.getDate() + offset);
    return isoDate(date);
  };

  const bucketKey = (date, mode) => {
    if (mode === "daily") return date;
    if (mode === "weekly") return startOfWeek(date);
    return date.slice(0, 7);
  };

  const bucketLabel = (date, mode) => {
    if (mode === "monthly") {
      const [year, month] = date.split("-");
      return `${monthNames[Number(month) - 1]} ${year}`;
    }

    const [, month, day] = date.split("-");
    return `${monthNames[Number(month) - 1]} ${Number(day)}`;
  };

  const aggregate = (days, mode) => {
    const buckets = new Map();

    days.forEach((day) => {
      const key = bucketKey(day.date, mode);
      const bucket = buckets.get(key) ?? { date: key, totalTokens: 0, models: {} };
      bucket.totalTokens += day.totalTokens;

      day.models.forEach((model) => {
        bucket.models[model.name] = (bucket.models[model.name] ?? 0) + modelTokens(model);
      });

      buckets.set(key, bucket);
    });

    return [...buckets.values()].sort((left, right) => left.date.localeCompare(right.date));
  };

  const cssColor = (property) => {
    const probe = document.createElement("span");
    probe.style.color = `var(${property})`;
    probe.hidden = true;
    document.body.appendChild(probe);
    const color = getComputedStyle(probe).color;
    probe.remove();
    return color;
  };

  const theme = () => {
    return {
      text: cssColor("--text-color"),
      title: cssColor("--title-color"),
      border: cssColor("--border-color"),
      surface: cssColor("--code-bg-color"),
      accent: cssColor("--link-color"),
    };
  };

  const colorFor = (index, alpha = 0.78) => {
    const [red, green, blue] = colors[index % colors.length];
    return `rgb(${red} ${green} ${blue} / ${alpha})`;
  };

  const tooltipTitle = (buckets, mode) => (items) => {
    const bucket = buckets[items[0].dataIndex];
    if (mode === "weekly") return `Week of ${bucket.date}`;
    return bucketLabel(bucket.date, mode);
  };

  const chartDefaults = (palette) => ({
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 250 },
    interaction: { intersect: false },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: palette.surface,
        titleColor: palette.title,
        bodyColor: palette.text,
        borderColor: palette.border,
        borderWidth: 1,
        cornerRadius: 4,
        padding: 10,
      },
    },
    scales: {
      x: {
        ticks: { color: palette.text, maxRotation: 45, autoSkip: true, maxTicksLimit: 18 },
        grid: { display: false },
        border: { color: palette.border },
      },
      y: {
        ticks: { color: palette.text, callback: compactNumber },
        grid: { color: palette.border, lineWidth: 0.5 },
        border: { display: false },
      },
    },
  });

  const destroyCharts = () => {
    charts.splice(0).forEach((chart) => chart.destroy());
  };

  const renderCharts = () => {
    destroyCharts();

    const buckets = aggregate(report.days, period);
    const labels = buckets.map((bucket) => bucketLabel(bucket.date, period));
    const palette = theme();
    const defaults = chartDefaults(palette);
    const title = tooltipTitle(buckets, period);
    const modelTotals = {};

    buckets.forEach((bucket) => {
      Object.entries(bucket.models).forEach(([model, tokens]) => {
        modelTotals[model] = (modelTotals[model] ?? 0) + tokens;
      });
    });

    const models = Object.entries(modelTotals)
      .sort((left, right) => right[1] - left[1])
      .map(([model]) => model);
    const legend = {
      display: true,
      position: "bottom",
      labels: {
        color: palette.text,
        boxWidth: 12,
        boxHeight: 12,
        padding: 14,
        usePointStyle: true,
        pointStyle: "rectRounded",
      },
    };

    charts.push(
      new Chart(root.querySelector("[data-usage-tokens]"), {
        type: "bar",
        data: {
          labels,
          datasets: [
            {
              data: buckets.map((bucket) => bucket.totalTokens),
              backgroundColor: palette.accent,
              borderRadius: 2,
            },
          ],
        },
        options: {
          ...defaults,
          plugins: {
            ...defaults.plugins,
            tooltip: {
              ...defaults.plugins.tooltip,
              callbacks: {
                title,
                label: (item) => `${compactNumber(item.raw)} tokens`,
              },
            },
          },
        },
      }),
    );

    const modelDatasets = models.map((model, index) => ({
      label: model,
      data: buckets.map((bucket) => bucket.models[model] ?? 0),
      backgroundColor: colorFor(index),
      borderColor: colorFor(index, 1),
      borderWidth: 0.5,
    }));

    charts.push(
      new Chart(root.querySelector("[data-usage-models]"), {
        type: "bar",
        data: { labels, datasets: modelDatasets },
        options: {
          ...defaults,
          plugins: {
            ...defaults.plugins,
            legend,
            tooltip: {
              ...defaults.plugins.tooltip,
              mode: "index",
              callbacks: {
                title,
                label: (item) =>
                  item.raw ? `${item.dataset.label}: ${compactNumber(item.raw)}` : null,
                footer: (items) =>
                  `Total: ${compactNumber(items.reduce((total, item) => total + item.raw, 0))}`,
              },
            },
          },
          scales: {
            ...defaults.scales,
            x: { ...defaults.scales.x, stacked: true },
            y: { ...defaults.scales.y, stacked: true },
          },
        },
      }),
    );

    const distributionDatasets = models.map((model, index) => ({
      label: model,
      data: buckets.map((bucket) => {
        const total = Object.values(bucket.models).reduce((sum, tokens) => sum + tokens, 0);
        return total ? ((bucket.models[model] ?? 0) / total) * 100 : 0;
      }),
      backgroundColor: colorFor(index),
      borderColor: colorFor(index, 1),
      borderWidth: 0.5,
    }));

    charts.push(
      new Chart(root.querySelector("[data-usage-distribution]"), {
        type: "bar",
        data: { labels, datasets: distributionDatasets },
        options: {
          ...defaults,
          plugins: {
            ...defaults.plugins,
            legend,
            tooltip: {
              ...defaults.plugins.tooltip,
              mode: "index",
              callbacks: {
                title,
                label: (item) =>
                  item.raw > 0 ? `${item.dataset.label}: ${item.raw.toFixed(1)}%` : null,
              },
            },
          },
          scales: {
            ...defaults.scales,
            x: { ...defaults.scales.x, stacked: true },
            y: {
              ...defaults.scales.y,
              stacked: true,
              min: 0,
              max: 100,
              ticks: { ...defaults.scales.y.ticks, callback: (value) => `${value}%` },
            },
          },
        },
      }),
    );
  };

  const renderPeriodToggle = () => {
    const toggle = root.querySelector("[data-usage-period]");
    toggle.replaceChildren();

    ["daily", "weekly", "monthly"].forEach((value) => {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = value[0].toUpperCase() + value.slice(1);
      button.className = value === period ? "active" : "";
      button.setAttribute("aria-pressed", String(value === period));
      button.addEventListener("click", () => {
        if (period === value) return;
        period = value;
        renderPeriodToggle();
        renderCharts();
      });
      toggle.appendChild(button);
    });
  };

  const renderActivity = () => {
    const container = root.querySelector("[data-usage-activity]");
    const usage = new Map(report.days.map((day) => [day.date, day.totalTokens]));
    const years = [...new Set(report.days.map((day) => day.date.slice(0, 4)))].sort();
    let selectedYear = years.at(-1);

    const renderYear = () => {
      container.replaceChildren();

      const start = new Date(`${selectedYear}-01-01T00:00:00`);
      const end = new Date(`${selectedYear}-12-31T00:00:00`);
      while (start.getDay() !== 1) start.setDate(start.getDate() - 1);
      while (end.getDay() !== 0) end.setDate(end.getDate() + 1);

      const days = [];
      for (const date = new Date(start); date <= end; date.setDate(date.getDate() + 1)) {
        const key = isoDate(date);
        days.push({ date: key, tokens: usage.get(key) ?? 0 });
      }

      const nonZero = days
        .map((day) => day.tokens)
        .filter(Boolean)
        .sort((left, right) => left - right);
      const quantile = (ratio) => nonZero[Math.floor(nonZero.length * ratio)] ?? 0;
      const thresholds = [quantile(0.25), quantile(0.5), quantile(0.75)];
      const level = (tokens) => {
        if (!tokens) return 0;
        if (tokens <= thresholds[0]) return 1;
        if (tokens <= thresholds[1]) return 2;
        if (tokens <= thresholds[2]) return 3;
        return 4;
      };
      const weeks = days.length / 7;

      const scroll = document.createElement("div");
      scroll.className = "usage-activity-scroll";
      const graph = document.createElement("div");
      graph.className = "usage-activity-graph";
      graph.style.setProperty("--usage-weeks", weeks);

      const months = document.createElement("div");
      months.className = "usage-activity-months";
      let previousMonth = "";
      for (let week = 0; week < weeks; week += 1) {
        const month = days[week * 7].date.slice(0, 7);
        if (month === previousMonth) continue;
        const label = document.createElement("span");
        label.textContent = monthNames[Number(month.slice(5)) - 1];
        label.style.gridColumnStart = week + 1;
        months.appendChild(label);
        previousMonth = month;
      }

      const body = document.createElement("div");
      body.className = "usage-activity-body";
      const weekdays = document.createElement("div");
      weekdays.className = "usage-activity-weekdays";
      ["Mon", "", "Wed", "", "Fri", "", ""].forEach((name) => {
        const label = document.createElement("span");
        label.textContent = name;
        weekdays.appendChild(label);
      });

      const grid = document.createElement("div");
      grid.className = "usage-activity-grid";
      days.forEach((day) => {
        const cell = document.createElement("span");
        cell.className = "usage-activity-cell";
        cell.dataset.level = level(day.tokens);
        cell.title = day.tokens
          ? `${day.date}: ${compactNumber(day.tokens)} tokens`
          : `${day.date}: no usage`;
        grid.appendChild(cell);
      });

      body.append(weekdays, grid);
      graph.append(months, body);
      scroll.appendChild(graph);

      const footer = document.createElement("div");
      footer.className = "usage-activity-footer";
      const yearToggle = document.createElement("div");
      yearToggle.className = "usage-year-toggle";
      years.forEach((year) => {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = year;
        button.className = year === selectedYear ? "active" : "";
        button.addEventListener("click", () => {
          selectedYear = year;
          renderYear();
        });
        yearToggle.appendChild(button);
      });

      const legend = document.createElement("div");
      legend.className = "usage-activity-legend";
      legend.append("Less");
      for (let value = 0; value <= 4; value += 1) {
        const cell = document.createElement("span");
        cell.className = "usage-activity-cell";
        cell.dataset.level = value;
        legend.appendChild(cell);
      }
      legend.append("More");

      footer.append(yearToggle, legend);
      container.append(scroll, footer);
    };

    renderYear();
  };

  const render = (data) => {
    if (!Array.isArray(data.days) || data.days.length === 0) {
      throw new Error("usage.json contains no daily data");
    }
    if (!window.Chart) throw new Error("Chart.js failed to load");

    report = data;
    root.querySelector(".usage-content").hidden = false;
    renderActivity();
    renderPeriodToggle();
    renderCharts();
    root.querySelector(".usage-status").remove();

    const rerenderCharts = () => requestAnimationFrame(renderCharts);
    new MutationObserver(rerenderCharts).observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme"],
    });
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", rerenderCharts);
  };

  fetch(root.dataset.usageUrl, { cache: "no-store" })
    .then((response) => {
      if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
      return response.json();
    })
    .then(render)
    .catch((error) => {
      const status = root.querySelector(".usage-status");
      if (status) {
        status.textContent = `Unable to load usage data: ${error.message}. Run pnpm stats first.`;
      }
    });
})();
