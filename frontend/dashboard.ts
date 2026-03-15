(function () {
    type MetricKey = "weight" | "visceral";
    type GraphMode = MetricKey | "both";
    type ChatRole = "user" | "bot";
    type FieldName =
        | "breakfast"
        | "lunch"
        | "dinner"
        | "weight_kg"
        | "visceral_fat_level"
        | "exercise"
        | "execution";

    interface ChartPoint {
        day: number;
        label: string;
        weight: number | null;
        visceral: number | null;
    }

    interface DashboardClientConfig {
        lifestyleImageMap: Record<"good" | "middle" | "bad", string>;
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

    type ScopeElement = HTMLElement & { dataset: DOMStringMap };
    type FieldElement = HTMLInputElement | HTMLSelectElement;

    const ALL_FIELDS: FieldName[] = [
        "breakfast",
        "lunch",
        "dinner",
        "weight_kg",
        "visceral_fat_level",
        "exercise",
        "execution"
    ];

    const COPY_FIELDS: Array<Extract<FieldName, "breakfast" | "lunch" | "dinner" | "weight_kg" | "visceral_fat_level">> = [
        "breakfast",
        "lunch",
        "dinner",
        "weight_kg",
        "visceral_fat_level"
    ];

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

    function queryAll<T extends Element>(selector: string, root: ParentNode = document): T[] {
        return Array.from(root.querySelectorAll<T>(selector));
    }

    function getCookie(name: string): string {
        const cookie = document.cookie
            .split(";")
            .map((value) => value.trim())
            .find((value) => value.startsWith(`${name}=`));
        return cookie ? decodeURIComponent(cookie.slice(name.length + 1)) : "";
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

    function getField(scope: ParentNode, fieldName: FieldName): FieldElement | null {
        return scope.querySelector<FieldElement>(`[data-field="${fieldName}"]`);
    }

    const chartPoints = parseJsonScript<ChartPoint[]>("chart-points-data") ?? [];
    const dashboardConfig = parseJsonScript<DashboardClientConfig>("dashboard-client-config") ?? {
        lifestyleImageMap: { good: "", middle: "", bad: "" }
    };

    const globalStatus = byId<HTMLElement>("global-status");
    const graphModalBackdrop = byId<HTMLElement>("graph-modal-backdrop");
    const openGraphModalButton = byId<HTMLButtonElement>("open-graph-modal");
    const closeGraphModalButton = byId<HTMLButtonElement>("close-graph-modal");
    const targetWeightInputNode = byId<HTMLInputElement>("target-weight-input");
    const graphModeButtons = queryAll<HTMLButtonElement>("[data-graph-mode]");
    const weightChartCard = document.querySelector<HTMLElement>('[data-chart-card="weight"]');
    const visceralChartCard = document.querySelector<HTMLElement>('[data-chart-card="visceral"]');
    const graphTooltip = byId<HTMLElement>("graph-tooltip");
    const chatFab = byId<HTMLButtonElement>("chat-fab");
    const chatPanel = byId<HTMLElement>("chat-panel");
    const chatForm = byId<HTMLFormElement>("chat-form");
    const chatInput = byId<HTMLInputElement>("chat-input");
    const todayScope = document.querySelector<ScopeElement>('.entry-scope[data-scope="today-card"]');

    const TARGET_WEIGHT_STORAGE_KEY = "daily_body_log_target_weight";
    const todayDate = todayScope?.dataset.date ?? "";
    const csrfToken = getCookie("csrftoken");
    const saveTimers = new Map<string, number>();

    if (!targetWeightInputNode) {
        return;
    }

    const targetWeightInput = targetWeightInputNode;

    let targetWeightSaveTimer: number | null = null;
    let graphMode: GraphMode = "weight";

    function loadTargetWeight(): void {
        if (!targetWeightInput) {
            return;
        }
        const savedValue = window.localStorage.getItem(TARGET_WEIGHT_STORAGE_KEY);
        if (savedValue) {
            targetWeightInput.value = savedValue;
        }
    }

    function persistTargetWeight(): void {
        if (!targetWeightInput) {
            return;
        }
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

    function showGraphTooltip(text: string, event: MouseEvent): void {
        if (!graphTooltip) {
            return;
        }
        graphTooltip.textContent = text;
        graphTooltip.style.left = `${event.clientX}px`;
        graphTooltip.style.top = `${event.clientY}px`;
        graphTooltip.classList.add("is-visible");
    }

    function hideGraphTooltip(): void {
        graphTooltip?.classList.remove("is-visible");
    }

    function bindGraphPointTooltip(svg: SVGSVGElement): void {
        queryAll<SVGElement>("[data-tooltip]", svg).forEach((node) => {
            node.addEventListener("mouseenter", (event) => {
                showGraphTooltip(node.dataset.tooltip ?? "", event);
            });
            node.addEventListener("mousemove", (event) => {
                showGraphTooltip(node.dataset.tooltip ?? "", event);
            });
            node.addEventListener("mouseleave", hideGraphTooltip);
            node.addEventListener("blur", hideGraphTooltip);
        });
    }

    function setMealSelectColor(select: HTMLSelectElement): void {
        Array.from(select.classList)
            .filter((name) => name.startsWith("meal-value-"))
            .forEach((name) => select.classList.remove(name));
        if (select.value) {
            select.classList.add(`meal-value-${select.value}`);
        }
    }

    function setAllMealSelectColors(root: ParentNode = document): void {
        queryAll<HTMLSelectElement>(".meal-select", root).forEach(setMealSelectColor);
    }

    function computeReplacementMealCount(scope: ParentNode): number {
        const breakfast = getField(scope, "breakfast")?.value ?? "";
        const lunch = getField(scope, "lunch")?.value ?? "";
        const dinner = getField(scope, "dinner")?.value ?? "";
        let count = 0;
        if (breakfast === "活力＋VM1122") {
            count += 1;
        }
        if (lunch === "D24＋推奨食事" || lunch === "D24＋ジュニアバランス") {
            count += 1;
        }
        if (dinner === "NB") {
            count += 1;
        }
        return count;
    }

    function computeRecommendedMealCount(scope: ParentNode): number {
        const meals = [
            getField(scope, "breakfast")?.value ?? "",
            getField(scope, "lunch")?.value ?? "",
            getField(scope, "dinner")?.value ?? ""
        ];
        return meals.filter((meal) => meal.includes("推奨食事")).length;
    }

    function updateAchievementMark(scope: ParentNode): void {
        const markNode = scope.querySelector<HTMLElement>("[data-achievement-mark]");
        if (!markNode) {
            return;
        }

        const breakfast = getField(scope, "breakfast")?.value ?? "";
        const lunch = getField(scope, "lunch")?.value ?? "";
        const dinner = getField(scope, "dinner")?.value ?? "";
        const replacementMealCount = computeReplacementMealCount(scope);
        const recommendedMealCount = computeRecommendedMealCount(scope);

        markNode.classList.remove("tone-good", "tone-middle", "tone-bad", "tone-empty");

        if (!breakfast && !lunch && !dinner) {
            markNode.textContent = "-";
            markNode.classList.add("tone-empty");
            markNode.dataset.tone = "empty";
            return;
        }

        if (replacementMealCount >= 2) {
            markNode.innerHTML = `<img src="${dashboardConfig.lifestyleImageMap.good}" alt="good">`;
            markNode.classList.add("tone-good");
            markNode.dataset.tone = "good";
            return;
        }

        if (replacementMealCount >= 1 || recommendedMealCount >= 2) {
            markNode.innerHTML = `<img src="${dashboardConfig.lifestyleImageMap.middle}" alt="middle">`;
            markNode.classList.add("tone-middle");
            markNode.dataset.tone = "middle";
            return;
        }

        markNode.innerHTML = `<img src="${dashboardConfig.lifestyleImageMap.bad}" alt="bad">`;
        markNode.classList.add("tone-bad");
        markNode.dataset.tone = "bad";
    }

    function setReplacementValues(scope: ScopeElement, mode: "2" | "3"): void {
        const breakfast = getField(scope, "breakfast");
        const lunch = getField(scope, "lunch");
        const dinner = getField(scope, "dinner");

        if (!(breakfast instanceof HTMLSelectElement) || !(lunch instanceof HTMLSelectElement) || !(dinner instanceof HTMLSelectElement)) {
            return;
        }

        breakfast.value = "活力＋VM1122";
        lunch.value = mode === "3" ? "D24＋ジュニアバランス" : "D24＋推奨食事";
        dinner.value = "NB";
        [breakfast, lunch, dinner].forEach(setMealSelectColor);
        updateAchievementMark(scope);
        scheduleSave(scope);
        syncTodayScopes(scope);
    }

    function syncTodayScopes(sourceScope: ScopeElement): void {
        if (!todayDate || sourceScope.dataset.date !== todayDate) {
            return;
        }

        queryAll<ScopeElement>(`.entry-scope[data-date="${todayDate}"]`).forEach((target) => {
            if (target === sourceScope) {
                return;
            }

            ALL_FIELDS.forEach((fieldName) => {
                const from = getField(sourceScope, fieldName);
                const to = getField(target, fieldName);
                if (!from || !to) {
                    return;
                }
                to.value = from.value;
                if (to instanceof HTMLSelectElement && to.classList.contains("meal-select")) {
                    setMealSelectColor(to);
                }
            });

            updateAchievementMark(target);
        });

        updateMonthlyExerciseTotal();
    }

    function parseExerciseMinutes(value: string): number {
        const text = value.trim();
        if (!text) {
            return 0;
        }

        let hours = 0;
        let minutes = 0;
        const hourMatch = text.match(/(\d+)時間/);
        const minuteMatch = text.match(/(\d+)分/);

        if (hourMatch?.[1]) {
            hours = Number.parseInt(hourMatch[1], 10);
        }
        if (minuteMatch?.[1]) {
            minutes = Number.parseInt(minuteMatch[1], 10);
        }

        return hours * 60 + minutes;
    }

    function formatExerciseMinutes(totalMinutes: number): string {
        const hours = Math.floor(totalMinutes / 60);
        const minutes = totalMinutes % 60;
        if (hours && minutes) {
            return `${hours}時間${minutes}分`;
        }
        if (hours) {
            return `${hours}時間`;
        }
        return `${minutes}分`;
    }

    function updateMonthlyExerciseTotal(): void {
        const totalNode = byId<HTMLElement>("monthly-total-exercise");
        if (!totalNode) {
            return;
        }

        const totalMinutes = queryAll<FieldElement>('.table-row [data-field="exercise"]')
            .reduce((sum, field) => sum + parseExerciseMinutes(field.value), 0);
        totalNode.textContent = formatExerciseMinutes(totalMinutes);
    }

    function showGlobalStatus(message: string, isError: boolean): void {
        if (!globalStatus) {
            return;
        }
        globalStatus.textContent = message;
        globalStatus.classList.toggle("error", isError);
    }

    async function saveScope(scope: ScopeElement): Promise<void> {
        const dateValue = scope.dataset.date ?? "";
        const formData = new FormData();

        ALL_FIELDS.forEach((fieldName) => {
            const field = getField(scope, fieldName);
            formData.append(fieldName, field?.value ?? "");
        });

        try {
            const response = await fetch(`/api/records/${dateValue}/`, {
                method: "POST",
                headers: { "X-CSRFToken": csrfToken },
                body: formData
            });
            const payload = await response.json() as { ok?: boolean; error?: string };
            if (!response.ok || !payload.ok) {
                throw new Error(payload.error ?? "保存に失敗しました");
            }

            updateAchievementMark(scope);
            syncTodayScopes(scope);
            showGlobalStatus(`${dateValue} を保存しました`, false);
        } catch (error) {
            const message = error instanceof Error ? error.message : "保存に失敗しました";
            showGlobalStatus(message, true);
        }
    }

    function scheduleSave(scope: ScopeElement): void {
        const key = scope.dataset.date ?? "";
        const existing = saveTimers.get(key);
        if (existing !== undefined) {
            window.clearTimeout(existing);
        }
        saveTimers.set(key, window.setTimeout(() => {
            void saveScope(scope);
        }, 260));
    }

    function getNavMatrix(): FieldElement[][] {
        return queryAll<ScopeElement>(".table-row").map((row) =>
            queryAll<FieldElement>("select[data-cell], input[data-cell]", row).sort(
                (left, right) => Number(left.dataset.cell ?? 0) - Number(right.dataset.cell ?? 0)
            )
        );
    }

    function focusRelative(current: FieldElement, rowOffset: number, colOffset: number): void {
        const matrix = getNavMatrix();
        const rowIndex = matrix.findIndex((row) => row.includes(current));
        if (rowIndex < 0) {
            return;
        }

        const colIndex = matrix[rowIndex].indexOf(current);
        const nextRowIndex = Math.min(Math.max(rowIndex + rowOffset, 0), matrix.length - 1);
        const nextRow = matrix[nextRowIndex];
        const nextColIndex = Math.min(Math.max(colIndex + colOffset, 0), nextRow.length - 1);
        nextRow[nextColIndex]?.focus();
    }

    function buildLinePath(
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

    function renderChart(svgId: string, metric: MetricKey, lineColor: string, targetValue: number | null): void {
        const svg = byId<SVGSVGElement>(svgId);
        if (!svg) {
            return;
        }

        const dims: ChartDimensions = { width: 920, height: 280, left: 54, right: 30, top: 18, bottom: 38 };
        const bounds = getMetricBounds(chartPoints.map((point) => point[metric]), targetValue);
        const usableWidth = dims.width - dims.left - dims.right;
        const usableHeight = dims.height - dims.top - dims.bottom;
        const xStep = usableWidth / Math.max(chartPoints.length - 1, 1);
        let html = "";

        hideGraphTooltip();

        for (let row = 0; row < 4; row += 1) {
            const y = dims.top + (usableHeight / 3) * row;
            const labelValue = (bounds.max - ((bounds.max - bounds.min) / 3) * row).toFixed(1);
            html += `<line x1="${dims.left}" y1="${y}" x2="${dims.width - dims.right}" y2="${y}" stroke="#e2eadb" stroke-width="1" />`;
            html += `<text x="8" y="${y + 5}" fill="${lineColor}" font-size="12">${labelValue}</text>`;
        }

        chartPoints.forEach((point, index) => {
            const x = dims.left + xStep * index;
            html += `<text x="${x}" y="${dims.height - 10}" fill="#607368" font-size="12" text-anchor="middle">${point.day}</text>`;
        });

        if (targetValue !== null) {
            const ratio = (targetValue - bounds.min) / Math.max(bounds.max - bounds.min, 0.0001);
            const y = dims.height - dims.bottom - ratio * usableHeight;
            html += `<line x1="${dims.left}" y1="${y}" x2="${dims.width - dims.right}" y2="${y}" stroke="#ef8c22" stroke-width="2" stroke-dasharray="8 6" />`;
        }

        const pathData = buildLinePath(chartPoints, metric, bounds, dims);
        if (pathData) {
            html += `<path d="${pathData}" fill="none" stroke="${lineColor}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />`;
        }

        chartPoints.forEach((point, index) => {
            if (point[metric] === null) {
                return;
            }
            const metricValue = point[metric];
            const x = dims.left + xStep * index;
            const ratio = (metricValue - bounds.min) / Math.max(bounds.max - bounds.min, 0.0001);
            const y = dims.height - dims.bottom - ratio * usableHeight;
            const tooltip = metric === "visceral"
                ? `${point.label} 体脂肪率 ${point.visceral?.toFixed(1) ?? ""}%`
                : `${point.label} 体重 ${point.weight?.toFixed(1) ?? ""}kg`;
            html += `<circle cx="${x}" cy="${y}" r="4.5" fill="${lineColor}" data-tooltip="${tooltip}" />`;
        });

        svg.innerHTML = html;
        bindGraphPointTooltip(svg);
    }

    function setGraphMode(mode: GraphMode): void {
        graphMode = mode;
        graphModeButtons.forEach((button) => {
            const isActive = button.dataset.graphMode === mode;
            button.classList.toggle("is-active", isActive);
            button.setAttribute("aria-pressed", isActive ? "true" : "false");
        });
        renderAllCharts();
    }

    function renderAllCharts(): void {
        if (!targetWeightInput) {
            return;
        }

        const parsed = targetWeightInput.value ? Number.parseFloat(targetWeightInput.value) : null;
        const targetValue = Number.isNaN(parsed) ? null : parsed;
        const showWeight = graphMode === "weight" || graphMode === "both";
        const showVisceral = graphMode === "visceral" || graphMode === "both";

        weightChartCard?.classList.toggle("is-hidden", !showWeight);
        visceralChartCard?.classList.toggle("is-hidden", !showVisceral);

        if (showWeight) {
            renderChart("weight-chart", "weight", "#2f6dcc", targetValue);
        }
        if (showVisceral) {
            renderChart("visceral-chart", "visceral", "#8a42bf", null);
        }
    }

    function appendChatMessage(role: ChatRole, message: string): void {
        const messages = byId<HTMLElement>("chat-messages");
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
            return "置き換え回数と食事メモを一緒に見ると、改善ポイントをつかみやすいです。";
        }
        if (message.includes("運動")) {
            return "まずは30分単位で続けられる運動を積み上げると、月合計でも変化が見やすいです。";
        }
        if (message.includes("体重")) {
            return "体重は日単位より週単位の流れで見るのがおすすめです。食事と運動も並べて確認してみてください。";
        }
        return "食事、運動、体重のどれを見るか書いてもらえれば、それに合わせて整理します。";
    }

    function ensureTodayPreviousButton(): void {
        if (!todayScope) {
            return;
        }

        const quickTitleGroup = todayScope.querySelector<HTMLElement>(".quick-title-group");
        const firstCountButton = quickTitleGroup?.querySelector<HTMLButtonElement>("[data-set-count]");
        if (!quickTitleGroup || !firstCountButton) {
            return;
        }

        queryAll<HTMLElement>("[data-use-previous]", quickTitleGroup).forEach((button) => button.remove());

        const button = document.createElement("button");
        button.type = "button";
        button.className = "prev-day-button";
        button.dataset.usePrevious = "";
        button.textContent = "前日";
        button.addEventListener("click", () => applyPreviousDayMetricsUniversal(todayScope));
        quickTitleGroup.insertBefore(button, firstCountButton);
    }

    function ensurePreviousDayHeaders(): void {
        queryAll<HTMLElement>(".table-scroll thead tr, .table-scroll .subheader-row").forEach((row) => {
            queryAll<HTMLElement>("th", row).forEach((header) => {
                if (header.textContent?.trim() === "前日") {
                    header.remove();
                }
            });
        });

        queryAll<ScopeElement>(".table-row").forEach((scope) => {
            queryAll<HTMLElement>('td > .prev-day-button[data-cell="6"]', scope).forEach((button) => {
                button.closest("td")?.remove();
            });

            const countTools = scope.querySelector<HTMLElement>(".count-tools");
            const firstCountButton = countTools?.querySelector<HTMLButtonElement>("[data-set-count]");
            if (!countTools || !firstCountButton) {
                return;
            }

            queryAll<HTMLElement>("[data-use-previous]", countTools).forEach((button) => button.remove());

            const button = document.createElement("button");
            button.type = "button";
            button.className = "prev-day-button";
            button.dataset.usePrevious = "";
            button.textContent = "前日";
            button.addEventListener("click", () => applyPreviousDayMetricsUniversal(scope));
            countTools.insertBefore(button, firstCountButton);
        });
    }

    function buildCountHelpNode(): HTMLSpanElement {
        const help = document.createElement("span");
        help.className = "count-help";
        help.tabIndex = 0;
        help.setAttribute("aria-label", "ボタンの説明");
        help.textContent = "?";

        const tooltip = document.createElement("span");
        tooltip.className = "count-help-tooltip";
        tooltip.textContent =
            "前日: 前日の朝食・昼食・夕食・体重・体脂肪率を入力\n" +
            "2: 2食置き換えの組み合わせを入力\n" +
            "3: 3食置き換えの組み合わせを入力";

        help.appendChild(tooltip);
        return help;
    }

    function ensureCountActionHelp(): void {
        const todayGroup = document.querySelector<HTMLElement>('.entry-scope[data-scope="today-card"] .quick-title-group');
        if (todayGroup) {
            queryAll<HTMLElement>(".count-help", todayGroup).forEach((node) => node.remove());
            todayGroup.appendChild(buildCountHelpNode());
        }

        queryAll<HTMLElement>(".table-row .count-tools").forEach((countTools) => {
            queryAll<HTMLElement>(".count-help", countTools).forEach((node) => node.remove());
        });

        queryAll<HTMLElement>(".table-scroll thead tr th:nth-child(2), .table-scroll .subheader-row th:nth-child(2)").forEach((headerCell) => {
            queryAll<HTMLElement>(".count-help", headerCell).forEach((node) => node.remove());
            headerCell.appendChild(buildCountHelpNode());
        });
    }

    function applyPreviousDayMetricsUniversal(scope: ScopeElement): void {
        const rows = queryAll<ScopeElement>(".table-row");
        let previousRow: ScopeElement | null = null;

        if (scope.classList.contains("table-row")) {
            const rowIndex = rows.indexOf(scope);
            previousRow = rowIndex > 0 ? rows[rowIndex - 1] : null;
        } else {
            const scopeDate = scope.dataset.date ?? "";
            const sortedRows = rows
                .filter((row) => (row.dataset.date ?? "") < scopeDate)
                .sort((a, b) => (a.dataset.date ?? "").localeCompare(b.dataset.date ?? ""));
            previousRow = sortedRows.length ? sortedRows[sortedRows.length - 1] : null;
        }

        if (!previousRow) {
            showGlobalStatus("前日の行がないため入力できません", true);
            return;
        }

        const missingField = COPY_FIELDS.some((fieldName) => !getField(previousRow, fieldName) || !getField(scope, fieldName));
        if (missingField) {
            showGlobalStatus("前日データの参照に失敗しました", true);
            return;
        }

        COPY_FIELDS.forEach((fieldName) => {
            const from = getField(previousRow as ParentNode, fieldName);
            const to = getField(scope, fieldName);
            if (!from || !to) {
                return;
            }
            to.value = from.value;
            if (to instanceof HTMLSelectElement && to.classList.contains("meal-select")) {
                setMealSelectColor(to);
            }
        });

        updateAchievementMark(scope);
        scheduleSave(scope);
        syncTodayScopes(scope);
        showGlobalStatus(`${scope.dataset.date ?? ""} に前日値を入力しました`, false);
    }

    queryAll<ScopeElement>(".entry-scope").forEach((scope) => {
        updateAchievementMark(scope);

        scope.querySelectorAll<FieldElement>("select, input").forEach((field) => {
            field.addEventListener("change", () => {
                if (field instanceof HTMLSelectElement && field.classList.contains("meal-select")) {
                    setMealSelectColor(field);
                    updateAchievementMark(scope);
                }
                if (field.name === "exercise") {
                    updateMonthlyExerciseTotal();
                }
                scheduleSave(scope);
                syncTodayScopes(scope);
            });

            field.addEventListener("input", () => {
                if (field instanceof HTMLInputElement && (field.type === "number" || field.name === "execution")) {
                    scheduleSave(scope);
                    syncTodayScopes(scope);
                }
            });

            field.addEventListener("keydown", (event) => {
                const keyboardEvent = event as KeyboardEvent;
                if (!field.closest(".table-row")) {
                    return;
                }
                if (keyboardEvent.key === "ArrowUp") {
                    keyboardEvent.preventDefault();
                    focusRelative(field, -1, 0);
                } else if (keyboardEvent.key === "ArrowDown") {
                    keyboardEvent.preventDefault();
                    focusRelative(field, 1, 0);
                } else if (keyboardEvent.key === "ArrowLeft" && (field instanceof HTMLSelectElement || field.selectionStart === 0)) {
                    keyboardEvent.preventDefault();
                    focusRelative(field, 0, -1);
                } else if (
                    keyboardEvent.key === "ArrowRight" &&
                    (field instanceof HTMLSelectElement || field.selectionStart === field.value.length)
                ) {
                    keyboardEvent.preventDefault();
                    focusRelative(field, 0, 1);
                }
            });
        });

        queryAll<HTMLButtonElement>("[data-set-count]", scope).forEach((button) => {
            const mode = button.dataset.setCount;
            if (mode === "2" || mode === "3") {
                button.addEventListener("click", () => setReplacementValues(scope, mode));
            }
        });

        queryAll<HTMLElement>("[data-use-previous]", scope).forEach((button) => {
            button.addEventListener("click", () => applyPreviousDayMetricsUniversal(scope));
        });
    });

    ensureTodayPreviousButton();
    ensurePreviousDayHeaders();
    ensureCountActionHelp();
    setAllMealSelectColors();
    updateMonthlyExerciseTotal();

    loadTargetWeight();

    graphModeButtons.forEach((button) => {
        const mode = button.dataset.graphMode;
        if (mode === "weight" || mode === "visceral" || mode === "both") {
            button.addEventListener("click", () => setGraphMode(mode));
        }
    });

    if (openGraphModalButton && closeGraphModalButton && graphModalBackdrop && targetWeightInput) {
        openGraphModalButton.addEventListener("click", () => {
            graphModalBackdrop.classList.add("is-open");
            renderAllCharts();
        });
        closeGraphModalButton.addEventListener("click", () => {
            hideGraphTooltip();
            graphModalBackdrop.classList.remove("is-open");
        });
        graphModalBackdrop.addEventListener("click", (event) => {
            if (event.target === graphModalBackdrop) {
                hideGraphTooltip();
                graphModalBackdrop.classList.remove("is-open");
            }
        });
        targetWeightInput.addEventListener("input", () => {
            renderAllCharts();
            scheduleTargetWeightSave();
        });
        targetWeightInput.addEventListener("change", persistTargetWeight);
        targetWeightInput.addEventListener("blur", persistTargetWeight);
    }

    if (chatFab && chatPanel) {
        chatFab.addEventListener("click", () => chatPanel.classList.toggle("is-open"));
    }

    queryAll<HTMLElement>("[data-suggestion]").forEach((button) => {
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
