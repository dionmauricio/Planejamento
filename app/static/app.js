"use strict";

const activeKey = document.body.dataset.activeSheet;
const titleNode = document.getElementById("sheet-title");
const descriptionNode = document.getElementById("sheet-description");
const summaryNode = document.getElementById("summary-cards");
const contentNode = document.getElementById("sheet-content");
const noticeNode = document.getElementById("notice");
const numberFormat = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 });
const percentFormat = new Intl.NumberFormat("pt-BR", {
  style: "percent",
  minimumFractionDigits: 1,
  maximumFractionDigits: 2,
});

function formatNumber(value) {
  return numberFormat.format(Number(value) || 0);
}

function formatPercent(value) {
  return percentFormat.format(Number(value) || 0);
}

function notify(message, isError = false) {
  noticeNode.textContent = message;
  noticeNode.classList.toggle("error", isError);
  noticeNode.hidden = false;
  window.clearTimeout(notify.timer);
  notify.timer = window.setTimeout(() => { noticeNode.hidden = true; }, 5500);
}

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined && text !== null) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function metric(label, value, foot, icon, valueClass = "") {
  const card = element("article", undefined, "metric-card");
  const top = element("div", undefined, "metric-top");
  top.append(element("span", label), element("span", icon, "metric-icon"));
  card.append(top, element("div", value, `metric-value ${valueClass}`.trim()));
  if (foot) card.append(element("div", foot, "metric-foot"));
  summaryNode.append(card);
}

function renderMetrics(data) {
  summaryNode.replaceChildren();
  const summary = data.summary || {};
  if (data.sheet.kind === "tasks") {
    metric("Tarefas cadastradas", formatNumber(summary.task_count), "Itens na base do cronograma", "T");
    metric("Peso planejado", `${formatNumber(summary.planned_kg)} kg`, "Soma dos pesos planejados", "P");
    metric("Peso fabricado", `${formatNumber(summary.actual_kg)} kg`, "Soma dos pesos fabricados", "F");
    metric("Avanço por peso", formatPercent(summary.progress), "Fabricado ÷ planejado", "%");
  } else if (data.sheet.kind === "areas") {
    metric("Áreas monitoradas", formatNumber(data.rows.length), "Conforme resumo da planilha", "A");
    metric("Peso planejado", `${formatNumber(summary.planned_kg)} kg`, "Total do resumo por área", "P");
    metric("Peso fabricado", `${formatNumber(summary.actual_kg)} kg`, "Total do resumo por área", "F");
    metric("Tarefas no resumo", formatNumber(summary.task_count), "Quantidade consolidada na origem", "T");
  } else {
    metric("Peso planejado total", `${formatNumber(summary.planned_kg)} kg`, "Base de cálculo do avanço físico", "P");
    metric("Peso fabricado", `${formatNumber(summary.actual_kg)} kg`, "Soma dos registros de produção", "F");
    metric("Avanço físico", formatPercent(summary.progress), "Peso fabricado ÷ peso planejado", "%");
    const currentDeviation = summary.as_of_deviation_kg ?? summary.deviation_kg;
    metric("Desvio na referência", `${formatNumber(currentDeviation)} kg`,
      `Acumulado em ${summary.as_of_date || "—"}`, "Δ",
      currentDeviation >= 0 ? "status-ok" : "status-late");
  }
}

function makePanel(heading, detail = "") {
  const panel = element("section", undefined, "panel");
  const bar = element("div", undefined, "panel-heading");
  const titleWrap = document.createElement("div");
  titleWrap.append(element("h2", heading));
  if (detail) titleWrap.append(element("p", detail));
  bar.append(titleWrap);
  panel.append(bar);
  return { panel, bar };
}

function chartPanel(data) {
  const { panel, bar } = makePanel(
    "Planejado x fabricado",
    "Evolução acumulada do avanço físico calculado por peso."
  );
  const legend = element("div", undefined, "legend");
  for (const [label, className] of [["Planejado", ""], ["Fabricado", "actual"]]) {
    const item = element("span", undefined, "legend-item");
    item.append(element("span", undefined, `legend-line ${className}`.trim()), element("span", label));
    legend.append(item);
  }
  bar.append(legend);
  const chart = element("div", undefined, "chart-wrap");
  if (!data.rows.length) {
    chart.append(element("div", "Sem dados importados para esta aba.", "chart-empty"));
    panel.append(chart);
    return panel;
  }

  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 900 230");
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", "Gráfico acumulado planejado versus fabricado");
  const left = 47;
  const top = 12;
  const width = 830;
  const height = 174;
  const maxValue = Math.max(1, ...data.rows.map((row) =>
    Math.max(row.planned_progress, row.actual_progress)));
  for (let tick = 0; tick <= 4; tick += 1) {
    const y = top + (height * tick) / 4;
    const grid = document.createElementNS(svg.namespaceURI, "line");
    grid.setAttribute("x1", String(left));
    grid.setAttribute("x2", String(left + width));
    grid.setAttribute("y1", String(y));
    grid.setAttribute("y2", String(y));
    grid.setAttribute("class", "grid-line");
    svg.append(grid);
    const label = document.createElementNS(svg.namespaceURI, "text");
    label.setAttribute("x", "0");
    label.setAttribute("y", String(y + 3));
    label.setAttribute("class", "axis-label");
    label.textContent = formatPercent(maxValue * (1 - tick / 4));
    svg.append(label);
  }
  for (const [field, className] of [
    ["planned_progress", "planned-line"],
    ["actual_progress", "actual-line"],
  ]) {
    const points = data.rows.map((row, index) => {
      const x = left + (data.rows.length === 1 ? 0 : (width * index) / (data.rows.length - 1));
      const y = top + height * (1 - row[field] / maxValue);
      return `${x},${y}`;
    }).join(" ");
    const line = document.createElementNS(svg.namespaceURI, "polyline");
    line.setAttribute("points", points);
    line.setAttribute("class", className);
    svg.append(line);
  }
  const first = document.createElementNS(svg.namespaceURI, "text");
  first.setAttribute("x", String(left));
  first.setAttribute("y", "222");
  first.setAttribute("class", "axis-label");
  first.textContent = data.rows[0].period_date;
  const last = document.createElementNS(svg.namespaceURI, "text");
  last.setAttribute("x", String(left + width));
  last.setAttribute("y", "222");
  last.setAttribute("text-anchor", "end");
  last.setAttribute("class", "axis-label");
  last.textContent = data.rows[data.rows.length - 1].period_date;
  svg.append(first, last);
  chart.append(svg);
  panel.append(chart);
  return panel;
}

function buildTable(headers, rows) {
  const panel = element("section", undefined, "panel");
  const scroller = element("div", undefined, "table-scroll");
  const table = document.createElement("table");
  const head = document.createElement("thead");
  const headRow = document.createElement("tr");
  headers.forEach((header) => headRow.append(element("th", header)));
  head.append(headRow);
  const body = document.createElement("tbody");
  rows.forEach((row) => body.append(row));
  table.append(head, body);
  scroller.append(table);
  panel.append(scroller);
  return panel;
}

function tableCell(text, className = "") {
  return element("td", text, className);
}

function renderCurve(data) {
  contentNode.replaceChildren(chartPanel(data));
  if (data.sheet.kind === "daily_curve" || data.sheet.kind === "weekly_curve") {
    const panel = makePanel("Apontamentos do período", "Informe o peso fabricado para recalcular os acumulados e desvios.");
    contentNode.append(panel.panel);
    if (!data.rows.length) {
      panel.panel.append(element("div", "Importe a planilha de origem para preencher este cronograma.", "empty-state"));
      return;
    }
    const tablePanel = buildTable(
      ["Período", "Peso planejado", "Planejado acumulado", "Avanço planejado", "Peso fabricado", "Fabricado acumulado", "Avanço fabricado", "Desvio kg", "Status", "Ação"],
      data.rows.map((row) => {
        const tr = document.createElement("tr");
        tr.append(
          tableCell(row.period_date),
          tableCell(`${formatNumber(row.planned_kg)} kg`, "numeric"),
          tableCell(`${formatNumber(row.planned_cumulative_kg)} kg`, "numeric"),
          tableCell(formatPercent(row.planned_progress), "numeric"),
        );
        const actualCell = document.createElement("td");
        const input = element("input");
        input.type = "number";
        input.min = "0";
        input.step = "0.001";
        input.value = row.actual_kg;
        input.setAttribute("aria-label", `Peso fabricado em ${row.period_date}`);
        input.className = "editable";
        actualCell.append(input);
        const buttonCell = document.createElement("td");
        const button = element("button", "Salvar", "button button-primary button-small");
        button.type = "button";
        button.dataset.action = "save-period";
        button.dataset.periodId = row.id === null ? "" : row.id;
        buttonCell.append(button);
        const progressCell = tableCell(formatNumber(row.actual_cumulative_kg), "numeric");
        tr.append(
          actualCell,
          progressCell,
          tableCell(formatPercent(row.actual_progress), "numeric"),
          tableCell(`${formatNumber(row.deviation_kg)} kg`, "numeric"),
        );
        const status = element("span", row.status, `status-pill ${row.status === "No prazo" ? "ok" : "late"}`);
        const statusCell = document.createElement("td");
        statusCell.append(status);
        tr.append(statusCell);
        tr.dataset.actualInput = "";
        tr.dataset.periodId = row.id === null ? "" : row.id;
        tr.append(buttonCell);
        return tr;
      })
    );
    panel.panel.append(tablePanel);
  } else {
    const panel = makePanel("Consolidação semanal", "Totais agrupados por semana a partir dos registros da curva diária.");
    const table = buildTable(
      ["Semana iniciada em", "Planejado (kg)", "Planejado acumulado (kg)", "Avanço planejado", "Fabricado (kg)", "Fabricado acumulado (kg)", "Avanço fabricado", "Desvio (kg)", "Status"],
      data.rows.map((row) => {
        const tr = document.createElement("tr");
        const status = element("span", row.status, `status-pill ${row.status === "No prazo" ? "ok" : "late"}`);
        const statusCell = document.createElement("td");
        statusCell.append(status);
        [
          row.period_date,
          `${formatNumber(row.planned_kg)} kg`,
          `${formatNumber(row.planned_cumulative_kg)} kg`,
          formatPercent(row.planned_progress),
          `${formatNumber(row.actual_kg)} kg`,
          `${formatNumber(row.actual_cumulative_kg)} kg`,
          formatPercent(row.actual_progress),
          `${formatNumber(row.deviation_kg)} kg`,
        ].forEach((value) => tr.append(tableCell(value)));
        tr.append(statusCell);
        return tr;
      })
    );
    panel.panel.append(table);
    if (!data.rows.length) panel.panel.append(element("div", "A planilha semanal original está vazia. Os dados aparecerão após importar a curva diária.", "empty-state"));
    contentNode.append(panel.panel);
  }
}

function renderTasks(data) {
  const formPanel = element("section", undefined, "panel form-panel");
  formPanel.append(element("h2", "Adicionar tarefa"));
  const form = element("form", undefined, "task-form");
  form.dataset.action = "create-task";
  const fields = [
    ["project_area", "Projeto / área", "text", true],
    ["drawing", "Desenho", "text", false],
    ["item_code", "Marca / item", "text", false],
    ["name", "Nome da tarefa", "text", true],
    ["starts_on", "Início", "datetime-local", false],
    ["ends_on", "Término", "datetime-local", false],
    ["planned_kg", "Peso planejado (kg)", "number", false],
    ["manufactured_kg", "Peso fabricado (kg)", "number", false],
    ["shipped_kg", "Peso expedido (kg)", "number", false],
  ];
  fields.forEach(([name, label, type, required]) => {
    const field = element("div", undefined, "field");
    const inputId = `new-task-${name}`;
    const labelNode = element("label", label);
    labelNode.htmlFor = inputId;
    const input = element("input");
    input.id = inputId;
    input.name = name;
    input.type = type;
    input.required = required;
    if (type === "number") {
      input.min = "0";
      input.step = "0.001";
      input.value = "0";
    }
    field.append(labelNode, input);
    form.append(field);
  });
  const action = element("div", undefined, "form-actions");
  const addButton = element("button", "Cadastrar tarefa", "button button-primary");
  addButton.type = "submit";
  action.append(addButton);
  form.append(action);
  formPanel.append(form);
  contentNode.append(formPanel);

  const table = buildTable(
    ["ID MS Project", "Linha banco de dados", "Projeto / área", "Desenho", "Marca", "Tarefa", "Início", "Término", "Planejado (kg)", "Fabricado (kg)", "Avanço", "Expedido (kg)", "Ação"],
    data.rows.map((task) => {
      const tr = document.createElement("tr");
      [
        task.source_id ?? task.id,
        task.database_row ?? "—",
        task.project_area,
        task.drawing,
        task.item_code,
        task.name,
        task.starts_on || "—",
        task.ends_on || "—",
      ].forEach((value) => tr.append(tableCell(value)));
      for (const [field, value] of [
        ["planned_kg", task.planned_kg],
        ["manufactured_kg", task.manufactured_kg],
      ]) {
        const td = document.createElement("td");
        const input = element("input");
        input.type = "number";
        input.min = "0";
        input.step = "0.001";
        input.value = value;
        input.dataset.field = field;
        input.className = "editable";
        input.setAttribute("aria-label", `${field} — ${task.name}`);
        td.append(input);
        tr.append(td);
      }
      tr.append(tableCell(formatPercent(task.progress)));
      const shippedCell = document.createElement("td");
      const shippedInput = element("input");
      shippedInput.type = "number";
      shippedInput.min = "0";
      shippedInput.step = "0.001";
      shippedInput.value = task.shipped_kg;
      shippedInput.dataset.field = "shipped_kg";
      shippedInput.className = "editable";
      shippedInput.setAttribute("aria-label", `Peso expedido — ${task.name}`);
      shippedCell.append(shippedInput);
      tr.append(shippedCell);
      const actions = element("td");
      const button = element("button", "Salvar", "button button-primary button-small");
      button.type = "button";
      button.dataset.action = "save-task";
      button.dataset.taskId = task.id;
      const removeButton = element("button", "Excluir", "button button-quiet button-small");
      removeButton.type = "button";
      removeButton.dataset.action = "delete-task";
      removeButton.dataset.taskId = task.id;
      actions.append(button, removeButton);
      tr.append(actions);
      return tr;
    })
  );
  if (!data.rows.length) table.append(element("div", "Nenhuma tarefa cadastrada. Use o formulário acima para adicionar o primeiro item.", "empty-state"));
  contentNode.append(table);
}

function renderAreas(data) {
  const panel = makePanel(
    "Indicadores por área",
    "Valores preservados da aba Resumo por Área do arquivo de origem."
  );
  const table = buildTable(
    ["Projeto / área", "Qtd. tarefas", "Peso planejado (kg)", "Peso fabricado (kg)", "Avanço por peso"],
    data.rows.map((area) => {
      const tr = document.createElement("tr");
      [
        area.project_area,
        formatNumber(area.task_count),
        formatNumber(area.planned_kg),
        formatNumber(area.manufactured_kg),
        formatPercent(area.progress),
      ].forEach((value) => tr.append(tableCell(value)));
      return tr;
    })
  );
  panel.panel.append(table);
  if (!data.rows.length) panel.panel.append(element("div", "Importe a planilha de origem para preencher o resumo.", "empty-state"));
  contentNode.replaceChildren(panel.panel);
}

async function loadSheet() {
  try {
    const response = await fetch(`/api/planilhas/${encodeURIComponent(activeKey)}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.description || data.error || "Não foi possível carregar a planilha.");
    titleNode.textContent = data.sheet.name;
    descriptionNode.textContent = data.sheet.description;
    document.title = `${data.sheet.name} | Planejamento JM Engenharia`;
    document.getElementById("export-link").href = `/exportar/${encodeURIComponent(activeKey)}.csv`;
    renderMetrics(data);
    if (["daily_curve", "weekly_curve", "weekly_summary"].includes(data.sheet.kind)) renderCurve(data);
    else if (data.sheet.kind === "tasks") renderTasks(data);
    else renderAreas(data);
  } catch (error) {
    contentNode.replaceChildren(element("div", error.message, "empty-state"));
    notify(error.message, true);
  }
}

contentNode.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  const row = button.closest("tr");
  try {
    if (button.dataset.action === "save-period") {
      if (!button.dataset.periodId) throw new Error("Esta consolidação é somente para consulta.");
      const input = row.querySelector("input");
      const response = await fetch(`/api/planilhas/${encodeURIComponent(activeKey)}/periodos/${button.dataset.periodId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ actual_kg: input.value }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.description || result.error || "Falha ao salvar o período.");
      notify("Apontamento salvo. Os acumulados e indicadores foram recalculados.");
    } else if (button.dataset.action === "save-task") {
      const values = {};
      row.querySelectorAll("input[data-field]").forEach((input) => { values[input.dataset.field] = input.value; });
      const response = await fetch(`/api/tarefas/${button.dataset.taskId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(values),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.description || result.error || "Falha ao salvar a tarefa.");
      notify("Pesos da tarefa atualizados.");
    } else if (button.dataset.action === "delete-task") {
      if (!window.confirm("Excluir esta tarefa? Esta ação não pode ser desfeita.")) return;
      const response = await fetch(`/api/tarefas/${button.dataset.taskId}`, { method: "DELETE" });
      if (!response.ok) {
        const result = await response.json();
        throw new Error(result.error || "Falha ao excluir a tarefa.");
      }
      notify("Tarefa excluída.");
    }
    await loadSheet();
  } catch (error) {
    notify(error.message, true);
  }
});

contentNode.addEventListener("submit", async (event) => {
  if (event.target.dataset.action !== "create-task") return;
  event.preventDefault();
  const payload = Object.fromEntries(new FormData(event.target).entries());
  try {
    const response = await fetch("/api/tarefas", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.description || result.error || "Falha ao cadastrar a tarefa.");
    notify("Tarefa cadastrada.");
    await loadSheet();
  } catch (error) {
    notify(error.message, true);
  }
});

loadSheet();
