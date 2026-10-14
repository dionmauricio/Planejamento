from __future__ import annotations

import csv
from datetime import datetime
from decimal import Decimal
from io import StringIO
from typing import Any

from flask import Flask, abort, g, jsonify, make_response, render_template, request
from werkzeug.exceptions import HTTPException
from sqlalchemy import select, text

from .domain import as_decimal, curve_rows, fraction, weekly_rows
from .models import AreaSummary, CurvePeriod, Task
from .sheets import SHEETS, SHEET_BY_KEY


def _sheet_data(session, key: str) -> dict[str, Any]:
    metadata = SHEET_BY_KEY[key]
    kind = metadata["kind"]
    if kind in {"daily_curve", "weekly_curve", "weekly_summary"}:
        curve_key = "curva-s" if kind == "weekly_summary" else key
        entries = list(
            session.scalars(
                select(CurvePeriod)
                .where(CurvePeriod.sheet_key == curve_key)
                .order_by(CurvePeriod.period_date, CurvePeriod.sequence)
            )
        )
        if kind == "weekly_summary":
            rows, summary = weekly_rows(entries)
        else:
            rows, summary = curve_rows(entries)
        return {"sheet": metadata, "summary": summary, "rows": rows}

    if kind == "tasks":
        tasks = list(session.scalars(select(Task).order_by(Task.source_row, Task.id)))
        rows = [
            {
                "id": task.id,
                "source_id": task.source_id,
                "database_row": task.database_row,
                "project_area": task.project_area,
                "drawing": task.drawing,
                "item_code": task.item_code,
                "name": task.name,
                "starts_on": task.starts_on.isoformat(timespec="seconds") if task.starts_on else None,
                "ends_on": task.ends_on.isoformat(timespec="seconds") if task.ends_on else None,
                "planned_kg": float(task.planned_kg),
                "manufactured_kg": float(task.manufactured_kg),
                "progress": float(fraction(task.manufactured_kg, task.planned_kg)),
                "shipped_kg": float(task.shipped_kg),
            }
            for task in tasks
        ]
        planned = sum((task.planned_kg for task in tasks), Decimal("0"))
        manufactured = sum((task.manufactured_kg for task in tasks), Decimal("0"))
        shipped = sum((task.shipped_kg for task in tasks), Decimal("0"))
        return {
            "sheet": metadata,
            "summary": {
                "task_count": len(rows),
                "planned_kg": float(planned),
                "actual_kg": float(manufactured),
                "shipped_kg": float(shipped),
                "progress": float(fraction(manufactured, planned)),
            },
            "rows": rows,
        }

    areas = list(session.scalars(select(AreaSummary).order_by(AreaSummary.project_area)))
    rows = [
        {
            "project_area": area.project_area,
            "task_count": area.task_count,
            "planned_kg": float(area.planned_kg),
            "manufactured_kg": float(area.manufactured_kg),
            "progress": float(fraction(area.manufactured_kg, area.planned_kg)),
        }
        for area in areas
    ]
    planned = sum((area.planned_kg for area in areas), Decimal("0"))
    manufactured = sum((area.manufactured_kg for area in areas), Decimal("0"))
    return {
        "sheet": metadata,
        "summary": {
            "task_count": sum(row["task_count"] for row in rows),
            "planned_kg": float(planned),
            "actual_kg": float(manufactured),
        },
        "rows": rows,
    }


def _json_object() -> dict[str, Any]:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        abort(400, description="O corpo da requisição deve ser um objeto JSON.")
    return payload


def _required_text(payload: dict[str, Any], name: str, label: str, maximum: int) -> str:
    value = payload.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} é obrigatório.")
    value = value.strip()
    if len(value) > maximum:
        raise ValueError(f"{label} deve ter no máximo {maximum} caracteres.")
    return value


def _optional_text(payload: dict[str, Any], name: str, label: str, maximum: int) -> str:
    value = payload.get(name, "")
    if not isinstance(value, str):
        raise ValueError(f"{label} deve ser um texto.")
    value = value.strip()
    if len(value) > maximum:
        raise ValueError(f"{label} deve ter no máximo {maximum} caracteres.")
    return value


def _optional_datetime(value: Any, label: str) -> datetime | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise ValueError(f"{label} deve estar no formato AAAA-MM-DD.")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{label} deve ser uma data e hora válidas.") from exc
    if parsed.tzinfo is not None:
        raise ValueError(f"{label} deve usar o horário local sem fuso.")
    return parsed


def _update_task_numbers(task: Task, payload: dict[str, Any]) -> None:
    for field, label in (
        ("planned_kg", "Peso planejado"),
        ("manufactured_kg", "Peso fabricado"),
        ("shipped_kg", "Peso expedido"),
    ):
        if field in payload:
            setattr(task, field, as_decimal(payload[field], label))


def register_routes(app: Flask) -> None:
    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException):
        if request.path.startswith("/api/"):
            return jsonify({"error": error.description}), error.code
        return error

    @app.before_request
    def open_session() -> None:
        g.db = app.extensions["db_session_factory"]()

    @app.teardown_request
    def close_session(error: BaseException | None) -> None:
        session = g.pop("db", None)
        if session is not None:
            if error is not None:
                session.rollback()
            session.close()

    @app.get("/")
    def index():
        key = request.args.get("aba", SHEETS[0]["key"])
        if key not in SHEET_BY_KEY:
            key = SHEETS[0]["key"]
        return render_template("dashboard.html", sheets=SHEETS, active_key=key)

    @app.get("/health")
    def health():
        g.db.execute(text("SELECT 1"))
        return jsonify({"status": "ok", "database": "connected"})

    @app.get("/api/planilhas")
    def list_sheets():
        return jsonify(SHEETS)

    @app.get("/api/planilhas/<key>")
    def get_sheet(key: str):
        if key not in SHEET_BY_KEY:
            abort(404)
        return jsonify(_sheet_data(g.db, key))

    @app.put("/api/planilhas/<key>/periodos/<int:period_id>")
    def update_period(key: str, period_id: int):
        if key not in SHEET_BY_KEY or SHEET_BY_KEY[key]["kind"] not in {
            "daily_curve",
            "weekly_curve",
        }:
            abort(404)
        payload = _json_object()
        if "actual_kg" not in payload:
            abort(400, description="Informe actual_kg.")
        period = g.db.get(CurvePeriod, period_id)
        if period is None or period.sheet_key != key:
            abort(404)
        try:
            period.actual_kg = as_decimal(payload["actual_kg"], "Peso fabricado")
        except ValueError as exc:
            abort(400, description=str(exc))
        g.db.commit()
        return jsonify({"id": period.id, "actual_kg": float(period.actual_kg)})

    @app.post("/api/tarefas")
    def create_task():
        payload = _json_object()
        try:
            task = Task(
                project_area=_required_text(payload, "project_area", "Projeto/Área", 200),
                drawing=_optional_text(payload, "drawing", "Desenho", 200),
                item_code=_optional_text(payload, "item_code", "Marca/Item", 120),
                name=_required_text(payload, "name", "Nome da tarefa", 400),
                starts_on=_optional_datetime(payload.get("starts_on"), "Início"),
                ends_on=_optional_datetime(payload.get("ends_on"), "Término"),
                planned_kg=as_decimal(payload.get("planned_kg", 0), "Peso planejado"),
                manufactured_kg=as_decimal(
                    payload.get("manufactured_kg", 0), "Peso fabricado"
                ),
                shipped_kg=as_decimal(payload.get("shipped_kg", 0), "Peso expedido"),
                source_id=None,
                source_row=0,
                database_row=None,
            )
            if task.starts_on and task.ends_on and task.starts_on > task.ends_on:
                raise ValueError("A data de início não pode ser posterior ao término.")
            g.db.add(task)
            g.db.commit()
        except ValueError as exc:
            g.db.rollback()
            abort(400, description=str(exc))
        return jsonify({"id": task.id}), 201

    @app.patch("/api/tarefas/<int:task_id>")
    def update_task(task_id: int):
        task = g.db.get(Task, task_id)
        if task is None:
            abort(404)
        payload = _json_object()
        try:
            _update_task_numbers(task, payload)
        except ValueError as exc:
            abort(400, description=str(exc))
        g.db.commit()
        return jsonify({"id": task.id, "status": "atualizado"})

    @app.put("/api/tarefas/<int:task_id>")
    def replace_task(task_id: int):
        task = g.db.get(Task, task_id)
        if task is None:
            abort(404)
        payload = _json_object()
        try:
            task.project_area = _required_text(payload, "project_area", "Projeto/Área", 200)
            task.drawing = _optional_text(payload, "drawing", "Desenho", 200)
            task.item_code = _optional_text(payload, "item_code", "Marca/Item", 120)
            task.name = _required_text(payload, "name", "Nome da tarefa", 400)
            task.starts_on = _optional_datetime(payload.get("starts_on"), "Início")
            task.ends_on = _optional_datetime(payload.get("ends_on"), "Término")
            _update_task_numbers(task, payload)
            if task.starts_on and task.ends_on and task.starts_on > task.ends_on:
                raise ValueError("A data de início não pode ser posterior ao término.")
        except ValueError as exc:
            g.db.rollback()
            abort(400, description=str(exc))
        g.db.commit()
        return jsonify({"id": task.id, "status": "atualizado"})

    @app.delete("/api/tarefas/<int:task_id>")
    def delete_task(task_id: int):
        task = g.db.get(Task, task_id)
        if task is None:
            abort(404)
        g.db.delete(task)
        g.db.commit()
        return "", 204

    @app.get("/exportar/<key>.csv")
    def export_sheet(key: str):
        if key not in SHEET_BY_KEY:
            abort(404)
        data = _sheet_data(g.db, key)
        output = StringIO()
        writer = csv.writer(output, delimiter=";")
        if SHEET_BY_KEY[key]["kind"] in {"daily_curve", "weekly_curve", "weekly_summary"}:
            writer.writerow(
                [
                    "Período",
                    "Peso planejado (kg)",
                    "Peso planejado acumulado (kg)",
                    "Avanço planejado (%)",
                    "Peso fabricado (kg)",
                    "Peso fabricado acumulado (kg)",
                    "Avanço fabricado (%)",
                    "Desvio acumulado (kg)",
                    "Desvio acumulado (%)",
                    "Status",
                ]
            )
            for row in data["rows"]:
                writer.writerow(
                    [
                        row["period_date"],
                        row["planned_kg"],
                        row["planned_cumulative_kg"],
                        row["planned_progress"],
                        row["actual_kg"],
                        row["actual_cumulative_kg"],
                        row["actual_progress"],
                        row["deviation_kg"],
                        row["deviation_progress"],
                        row["status"],
                    ]
                )
        elif SHEET_BY_KEY[key]["kind"] == "tasks":
            writer.writerow(
                [
                    "ID MS Project",
                    "Linha Banco de Dados",
                    "Projeto/Área",
                    "Desenho",
                    "Marca/Item",
                    "Nome da Tarefa",
                    "Início",
                    "Término",
                    "Peso planejado (kg)",
                    "Peso fabricado (kg)",
                    "Avanço por peso (%)",
                    "Peso expedido (kg)",
                ]
            )
            for row in data["rows"]:
                writer.writerow(
                    [
                        row["source_id"],
                        row["database_row"],
                        row["project_area"],
                        row["drawing"],
                        row["item_code"],
                        row["name"],
                        row["starts_on"],
                        row["ends_on"],
                        row["planned_kg"],
                        row["manufactured_kg"],
                        row["progress"],
                        row["shipped_kg"],
                    ]
                )
        else:
            writer.writerow(
                [
                    "Projeto/Área",
                    "Qtd. tarefas",
                    "Peso planejado (kg)",
                    "Peso fabricado (kg)",
                    "Avanço (%)",
                ]
            )
            for row in data["rows"]:
                writer.writerow(
                    [
                        row["project_area"],
                        row["task_count"],
                        row["planned_kg"],
                        row["manufactured_kg"],
                        row["progress"],
                    ]
                )
        response = make_response("\ufeff" + output.getvalue())
        response.headers["Content-Type"] = "text/csv; charset=utf-8"
        response.headers["Content-Disposition"] = (
            f"attachment; filename={key}.csv"
        )
        return response
