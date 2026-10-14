from __future__ import annotations

SHEETS = [
    {
        "key": "curva-s",
        "name": "Curva S",
        "kind": "daily_curve",
        "description": "Planejamento diário e avanço físico acumulado por peso fabricado.",
    },
    {
        "key": "indicadores-semanais",
        "name": "Indicadores Semanais",
        "kind": "weekly_summary",
        "description": "Consolidado semanal calculado a partir da curva diária.",
    },
    {
        "key": "curva-s-preparacao",
        "name": "Curva S Preparação",
        "kind": "weekly_curve",
        "description": "Planejamento e produção semanal da etapa de preparação.",
    },
    {
        "key": "curva-s-montagem",
        "name": "Curva S Montagem",
        "kind": "weekly_curve",
        "description": "Planejamento e produção semanal da etapa de montagem.",
    },
    {
        "key": "curva-s-soldagem",
        "name": "Curva S Soldagem",
        "kind": "weekly_curve",
        "description": "Planejamento e produção semanal da etapa de soldagem.",
    },
    {
        "key": "curva-s-acabamento",
        "name": "Curva S Acabamento",
        "kind": "weekly_curve",
        "description": "Planejamento e produção semanal da etapa de acabamento.",
    },
    {
        "key": "curva-s-pintura",
        "name": "Curva S Pintura",
        "kind": "weekly_curve",
        "description": "Planejamento e produção semanal da etapa de pintura.",
    },
    {
        "key": "base-tarefas",
        "name": "Base Tarefas",
        "kind": "tasks",
        "description": "Itens do cronograma, pesos planejados, fabricados e expedidos.",
    },
    {
        "key": "resumo-por-area",
        "name": "Resumo por Área",
        "kind": "areas",
        "description": "Resumo por área preservado conforme a aba original da planilha.",
    },
]

SHEET_BY_KEY = {sheet["key"]: sheet for sheet in SHEETS}
