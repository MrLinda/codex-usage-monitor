from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.collectors.log_collector import MODEL_PRICING, calc_cost, cost_factor, has_pricing
from app.storage.repository import Repository

logger = logging.getLogger("codex_usage_monitor")


def pricing_fingerprint(
    model_aliases: dict[str, str] | None = None,
    model_multipliers: dict[str, float] | None = None,
) -> tuple:
    """当前定价相关配置的指纹：定价表 / 别名 / 折扣系数任一变化则指纹不同。

    采集循环用它判断是否需要重算全库——指纹没变时重算必然是空操作，直接跳过。
    """
    return (
        repr(MODEL_PRICING),
        tuple(sorted((model_aliases or {}).items())),
        tuple(sorted((k, str(v)) for k, v in (model_multipliers or {}).items())),
    )


def reprice_usage(
    repo: Repository,
    model_aliases: dict[str, str] | None = None,
    model_multipliers: dict[str, float] | None = None,
) -> int:
    """按"当前定价表 × 折扣系数"重算全库费用，回写有差异的行，返回回写行数。

    统一处理三类变更，历史数据跟随缩放：
    - 新模型补上了定价（原先 cost=0 的行补算出来）
    - 定价表调整（旧行按新牌价收敛）
    - 按型号折扣系数修改（config.toml 或 GUI 保存后生效）

    没有定价的型号跳过不动（保持原值，通常为 0），并按型号汇总警告一次。

    幂等：重算与存入走同一套 calc_cost，浮点位级一致，值没变的行不回写。
    """
    rows = repo.get_costable_rows()
    if not rows:
        return 0

    aliases = model_aliases or {}
    updates: list[tuple[float, int]] = []
    missing_models: set[str] = set()
    for r in rows:
        if not has_pricing(r["model"], aliases):
            missing_models.add(r["model"])
            continue
        cost = (
            calc_cost(
                r["model"], r["input_tokens"], r["output_tokens"], r["cached_input_tokens"], aliases
            )
            * cost_factor(r["model"], aliases, model_multipliers)
        )
        old = r["estimated_cost_usd"]
        if old is not None and old == cost:
            continue  # IEEE double 经 SQLite 往返位级一致，值没变就不回写
        updates.append((cost, r["id"]))

    if missing_models:
        # 每个未匹配型号只警告一次（不逐行刷屏）
        logger.warning(
            "No pricing for models (cost stays as-is): %s", ", ".join(sorted(missing_models))
        )

    if not updates:
        return 0

    changed = repo.update_costs(updates)
    if changed:
        total = sum(c for c, _ in updates)
        msg = (
            f"Pricing reprice: updated {changed} rows to current pricing/multipliers "
            f"(${total:.4f} total)"
        )
        logger.info(msg)
        repo.insert_event(datetime.now(timezone.utc), "pricing_reprice", msg)
    return changed
