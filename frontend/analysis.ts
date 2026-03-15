(function () {
    type MetricMode = "weight" | "visceral" | "both";
    type MetricKey = "weight" | "visceral";

    interface ChartPoint {
        day: number;
        label: string;
        weight: number | null;
        visceral: number | null;
    }

    interface Bounds {
        min: number;
        max: number;
    }

    interface ChartDimensions {
        width: number;
        height: number;
        left: number;
        right: number;
        top: number;
        bottom: number;
    }

    function parseJsonScript<T>(id: string): T | null {
        const node = document.getElementById(id);
        if (!(node instanceof HTMLScriptElement) || !node.textContent) {
            return null;
        }
        return JSON.parse(node.textContent) as T;
    }

    function byId<T extends Element>(id: string): T | null {
        const node = document.getElementById(id);
        return node as T | null;
    }

    function getMetricBounds(values: Array<number | null>, targetValue: number | null): Bounds {
        const filtered = values.filter((value): value is number => value !== null);
        if (targetValue !== null) {
            filtered.push(targetValue);
        }
        if (!filtered.length) {
            return { min: 0, max: 1 };
        }
        const min = Math.min(...filtered);
        const max = Math.max(...filtered);
        const pad = Math.max((max - min) * 0.15, 0.6);
        return { min: Math.max(0, min - pad), max: max + pad };
    }

    function showTooltip(node: HTMLElement | null, text: string, event: MouseEvent): void {
        if (!node) {
            return;
        }
        node.textContent = text;
        node.style.left = `${event.clientX}px`;
        node.style.top = `${event.clientY}px`;
        node.classList.add("is-visible");
    }

    function hideTooltip(node: HTMLElement | null): void {
        node?.classList.remove("is-visible");
    }

    const chartPoints = parseJsonScript<ChartPoint[]>("analysis-chart-points") ?? [];
    const targetWeightInputNode = byId<HTMLInputElement>("target-weight-input");
    const metricModeButtons = Array.from(document.querySelectorAll<HTMLButtonElement>("[data-metric-mode]"));
    const chartTooltip = byId<HTMLDivElement>("chart-tooltip");
    const calendarNoteTooltip = byId<HTMLDivElement>("calendar-note-tooltip");
    const chatFab = byId<HTMLButtonElement>("chat-fab");
    const chatPanel = byId<HTMLElement>("chat-panel");
    const chatForm = byId<HTMLFormElement>("chat-form");
    const chatInput = byId<HTMLInputElement>("chat-input");
    const TARGET_WEIGHT_STORAGE_KEY = "daily_body_log_target_weight";

    if (!targetWeightInputNode) {
        return;
    }
    const targetWeightInput = targetWeightInputNode;

    let targetWeightSaveTimer: number | null = null;
    let chartMetricMode: MetricMode = "weight";

    function loadTargetWeight(): void {
        const savedValue = window.localStorage.getItem(TARGET_WEIGHT_STORAGE_KEY);
        if (savedValue) {
            targetWeightInput.value = savedValue;
        }
    }

    function persistTargetWeight(): void {
        const value = targetWeightInput.value.trim();
        if (value) {
            window.localStorage.setItem(TARGET_WEIGHT_STORAGE_KEY, value);
            return;
        }
        window.localStorage.removeItem(TARGET_WEIGHT_STORAGE_KEY);
    }

    function scheduleTargetWeightSave(): void {
        if (targetWeightSaveTimer !== null) {
            window.clearTimeout(targetWeightSaveTimer);
        }
        targetWeightSaveTimer = window.setTimeout(persistTargetWeight, 250);
    }

    function bindPointTooltip(svg: SVGSVGElement): void {
        svg.querySelectorAll<SVGElement>("[data-tooltip]").forEach((node) => {
            node.addEventListener("mouseenter", (event) => {
                showTooltip(chartTooltip, node.dataset.tooltip ?? "", event);
            });
            node.addEventListener("mousemove", (event) => {
                showTooltip(chartTooltip, node.dataset.tooltip ?? "", event);
            });
            node.addEventListener("mouseleave", () => hideTooltip(chartTooltip));
            node.addEventListener("blur", () => hideTooltip(chartTooltip));
        });
    }

    function bindCalendarNoteTooltip(): void {
        document.querySelectorAll<HTMLElement>(".calendar-cell").forEach((cell) => {
            const note = (cell.dataset.note ?? "").trim();
            if (!note) {
                return;
            }
            cell.classList.add("has-note");
            cell.addEventListener("mouseenter", (event) => showTooltip(calendarNoteTooltip, note, event));
            cell.addEventListener("mousemove", (event) => showTooltip(calendarNoteTooltip, note, event));
            cell.addEventListener("mouseleave", () => hideTooltip(calendarNoteTooltip));
        });
    }

    function buildScaledPath(
        points: ChartPoint[],
        metric: MetricKey,
        bounds: Bounds,
        dims: ChartDimensions
    ): string {
        const usableWidth = dims.width - dims.left - dims.right;
        const usableHeight = dims.height - dims.top - dims.bottom;
        const validPoints = points.filter((point): point is ChartPoint & Record<MetricKey, number> => point[metric] !== null);

        return validPoints.map((point, index) => {
            const metricValue = point[metric];
            const x = dims.left + ((point.day - 1) / Math.max(points.length - 1, 1)) * usableWidth;
            const ratio = (metricValue - bounds.min) / Math.max(bounds.max - bounds.min, 0.0001);
            const y = dims.height - dims.bottom - ratio * usableHeight;
            return `${index === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
        }).join(" ");
    }

    function renderCombinedChart(targetValue: number | null, metricMode: MetricMode): void {
        const svg = byId<SVGSVGElement>("combined-chart");
        if (!svg) {
            return;
        }

        const dims: ChartDimensions = { width: 1280, height: 420, left: 72, right: 72, top: 24, bottom: 48 };
        const showWeight = metricMode === "weight" || metricMode === "both";
        const showVisceral = metricMode === "visceral" || metricMode === "both";
        const weightBounds = getMetricBounds(chartPoints.map((point) => point.weight), targetValue);
        const visceralBounds = getMetricBounds(chartPoints.map((point) => point.visceral), null);
        const usableWidth = dims.width - dims.left - dims.right;
        const usableHeight = dims.height - dims.top - dims.bottom;
        const xStep = usableWidth / Math.max(chartPoints.length - 1, 1);
        let html = "";

        hideTooltip(chartTooltip);

        for (let row = 0; row < 4; row += 1) {
            const y = dims.top + (usableHeight / 3) * row;
            html += `<line x1="${dims.left}" y1="${y}" x2="${dims.width - dims.right}" y2="${y}" stroke="#e2eadb" stroke-width="1" />`;
            if (showWeight) {
                const leftValue = (weightBounds.max - ((weightBounds.max - weightBounds.min) / 3) * row).toFixed(1);
                html += `<text x="8" y="${y + 5}" fill="#2f6dcc" font-size="14">${leftValue}</text>`;
            }
            if (showVisceral) {
                const rightValue = (visceralBounds.max - ((visceralBounds.max - visceralBounds.min) / 3) * row).toFixed(1);
                html += `<text x="${dims.width - 8}" y="${y + 5}" fill="#8a42bf" font-size="14" text-anchor="end">${rightValue}</text>`;
            }
        }

        chartPoints.forEach((point, index) => {
            const x = dims.left + xStep * index;
            html += `<text x="${x}" y="${dims.height - 10}" fill="#607368" font-size="14" text-anchor="middle">${point.label}</text>`;
        });

        if (targetValue !== null && showWeight) {
            const ratio = (targetValue - weightBounds.min) / Math.max(weightBounds.max - weightBounds.min, 0.0001);
            const y = dims.height - dims.bottom - ratio * usableHeight;
            html += `<line x1="${dims.left}" y1="${y}" x2="${dims.width - dims.right}" y2="${y}" stroke="#ef8c22" stroke-width="2" stroke-dasharray="8 6" />`;
            html += `<text x="${dims.width - dims.right}" y="${y - 10}" fill="#ef8c22" font-size="24" font-weight="800" text-anchor="end">目標 ${targetValue.toFixed(1)}kg</text>`;
        }

        const weightPath = buildScaledPath(chartPoints, "weight", weightBounds, dims);
        const visceralPath = buildScaledPath(chartPoints, "visceral", visceralBounds, dims);

        if (showWeight && weightPath) {
            html += `<path d="${weightPath}" fill="none" stroke="#2f6dcc" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />`;
        }
        if (showVisceral && visceralPath) {
            html += `<path d="${visceralPath}" fill="none" stroke="#8a42bf" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />`;
        }

        if (showWeight) {
            chartPoints.forEach((point, index) => {
                if (point.weight === null) {
                    return;
                }
                const x = dims.left + xStep * index;
                const ratio = (point.weight - weightBounds.min) / Math.max(weightBounds.max - weightBounds.min, 0.0001);
                const y = dims.height - dims.bottom - ratio * usableHeight;
                html += `<circle cx="${x}" cy="${y}" r="4.5" fill="#2f6dcc" data-tooltip="${point.label} 体重 ${point.weight.toFixed(1)}kg" />`;
            });
        }

        if (showVisceral) {
            chartPoints.forEach((point, index) => {
                if (point.visceral === null) {
                    return;
                }
                const x = dims.left + xStep * index;
                const ratio = (point.visceral - visceralBounds.min) / Math.max(visceralBounds.max - visceralBounds.min, 0.0001);
                const y = dims.height - dims.bottom - ratio * usableHeight;
                html += `<circle cx="${x}" cy="${y}" r="4.5" fill="#8a42bf" data-tooltip="${point.label} 体脂肪率 ${point.visceral.toFixed(1)}%" />`;
            });
        }

        svg.innerHTML = html;
        bindPointTooltip(svg);
    }

    function setMetricMode(mode: MetricMode): void {
        chartMetricMode = mode;
        metricModeButtons.forEach((button) => {
            const isActive = button.dataset.metricMode === mode;
            button.classList.toggle("is-active", isActive);
            button.setAttribute("aria-pressed", isActive ? "true" : "false");
        });
        renderAllCharts();
    }

    function renderAllCharts(): void {
        const parsed = targetWeightInput.value ? Number.parseFloat(targetWeightInput.value) : null;
        renderCombinedChart(Number.isNaN(parsed) ? null : parsed, chartMetricMode);
    }

    function appendChatMessage(role: "user" | "bot", message: string): void {
        const messages = byId<HTMLDivElement>("chat-messages");
        if (!messages) {
            return;
        }
        const row = document.createElement("div");
        row.className = "chat-row";
        const bubble = document.createElement("div");
        bubble.className = `chat-bubble ${role}`;
        bubble.textContent = message;
        row.appendChild(bubble);
        messages.appendChild(row);
        row.scrollIntoView({ block: "end" });
    }

    function buildChatReply(message: string): string {
        if (message.includes("食事")) {
            return "主食と主菜の量を少し整えつつ、置き換えの回数を増やす進め方が扱いやすいです。";
        }
        if (message.includes("運動")) {
            return "まずは1日30分を目安に、無理なく続けられる運動を積み上げるのが安定します。";
        }
        if (message.includes("体重")) {
            return "日ごとの増減より、数日単位の流れを見るのがおすすめです。食事と運動を一緒に見ると判断しやすくなります。";
        }
        return "食事、運動、体重のどれを見たいかを書いてもらえれば、それに合わせて整理します。";
    }

    loadTargetWeight();
    metricModeButtons.forEach((button) => {
        const mode = button.dataset.metricMode;
        if (mode === "weight" || mode === "visceral" || mode === "both") {
            button.addEventListener("click", () => setMetricMode(mode));
        }
    });

    targetWeightInput.addEventListener("input", () => {
        renderAllCharts();
        scheduleTargetWeightSave();
    });
    targetWeightInput.addEventListener("change", persistTargetWeight);
    targetWeightInput.addEventListener("blur", persistTargetWeight);

    renderAllCharts();
    bindCalendarNoteTooltip();

    if (chatFab && chatPanel) {
        chatFab.addEventListener("click", () => chatPanel.classList.toggle("is-open"));
    }

    document.querySelectorAll<HTMLElement>("[data-suggestion]").forEach((button) => {
        button.addEventListener("click", () => {
            const message = button.dataset.suggestion ?? "";
            appendChatMessage("user", message);
            appendChatMessage("bot", buildChatReply(message));
        });
    });

    if (chatForm && chatInput) {
        chatForm.addEventListener("submit", (event) => {
            event.preventDefault();
            const message = chatInput.value.trim();
            if (!message) {
                return;
            }
            appendChatMessage("user", message);
            appendChatMessage("bot", buildChatReply(message));
            chatInput.value = "";
        });
    }
}());
