"""WebSocket endpoint: /ws/parse

Protocol
--------
Client → Server (JSON, once):
    {
        "source": "/path/to/repo | https://github.com/...",
        "config": {                          # optional
            "include_test_files": false,
            "max_workers": 4,
            "supported_languages": ["python", "java"]
        }
    }

Server → Client (JSON stream):
    {"type": "log",      "message": "..."}
    {"type": "progress", "current": 5, "total": 100, "percent": 5.0,
                         "file": "src/App.java", "nodes_so_far": 12, "edges_so_far": 8}
    ...
    {"type": "complete", "repo_id": "...", "language": "python",
                         "node_count": 200, "edge_count": 450,
                         "error_count": 2, "duration_ms": 3200}

    or on fatal error:
    {"type": "error", "detail": "Cannot access path: ..."}
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from parsers.config import IngestionConfig
from parsers.models import ProgressUpdate
from parsers.parallel_runner import parse_repository

logger = logging.getLogger(__name__)

router = APIRouter(tags=["parse"])


@router.websocket("/ws/parse")
async def ws_parse(websocket: WebSocket) -> None:  # noqa: ANN201
    """Stream parsing progress and deliver the final result over WebSocket."""
    await websocket.accept()
    logger.info("WebSocket /ws/parse accepted from %s", websocket.client)

    try:
        # ── Receive initial message ───────────────────────────────────────────
        msg = await websocket.receive_json()
        source: str = msg.get("source", "").strip()
        if not source:
            await websocket.send_json({"type": "error", "detail": "Missing 'source' field."})
            await websocket.close()
            return

        # ── Build config from optional override keys ──────────────────────────
        raw_cfg: dict = msg.get("config", {}) or {}
        config = IngestionConfig(
            include_test_files=raw_cfg.get("include_test_files", False),
            max_workers=raw_cfg.get("max_workers", IngestionConfig().max_workers),
            supported_languages=raw_cfg.get("supported_languages", IngestionConfig().supported_languages),
        )

        # ── Progress callback ─────────────────────────────────────────────────
        async def send_progress(update: ProgressUpdate) -> None:
            try:
                await websocket.send_json(update.to_dict())
            except Exception:  # noqa: BLE001
                pass  # client disconnected mid-stream

        # ── Run analysis ──────────────────────────────────────────────────────
        result = await parse_repository(source, config, progress_callback=send_progress)

        # ── Send completion summary ───────────────────────────────────────────
        await websocket.send_json(
            {
                "type": "complete",
                "repo_id": result.repo_id,
                "source": result.source,
                "language": result.language,
                "node_count": result.node_count,
                "edge_count": result.edge_count,
                "error_count": result.error_count,
                "files_parsed": result.files_parsed,
                "files_skipped": result.files_skipped,
                "duration_ms": round(result.duration_ms, 1),
                "errors": result.errors[:20],  # cap to avoid huge payloads
            }
        )

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected during parse")
    except ValueError as exc:
        logger.warning("Parse input error: %s", exc)
        try:
            await websocket.send_json({"type": "error", "detail": str(exc)})
        except Exception:  # noqa: BLE001
            pass
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error in ws_parse")
        try:
            await websocket.send_json({"type": "error", "detail": f"Internal error: {exc}"})
        except Exception:  # noqa: BLE001
            pass
    finally:
        try:
            await websocket.close()
        except Exception:  # noqa: BLE001
            pass
