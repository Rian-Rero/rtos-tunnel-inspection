#!/usr/bin/env python3
"""
Analisa os dados de timing das tarefas periódicas do RTOS e gera:
  - Gráfico de jitter de wakeup por ciclo
  - Gráfico de tempo de execução por ciclo (com linha de deadline)
  - Gantt mostrando execução simultânea das tarefas

Uso:
    python analyze_timing.py [caminho_do_csv]

Por padrão lê: data/logs/task_timing.csv
"""

import sys
import csv
from collections import defaultdict
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

LOG_PATH = Path("data/logs/task_timing.csv")
GANTT_WINDOW_MS = 500  # primeiros N ms exibidos no Gantt


# ── Leitura ──────────────────────────────────────────────────────────────────


def load(path: Path) -> dict:
    tasks = defaultdict(
        lambda: {
            "period_ms": 0,
            "cycles": [],
            "scheduled": [],
            "actual": [],
            "exec_end": [],
        }
    )
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            name = row["task_name"]
            tasks[name]["period_ms"] = int(row["period_ms"])
            tasks[name]["cycles"].append(int(row["cycle_num"]))
            tasks[name]["scheduled"].append(int(row["scheduled_ns"]))
            tasks[name]["actual"].append(int(row["actual_ns"]))
            tasks[name]["exec_end"].append(int(row["exec_end_ns"]))
    return {
        k: {f: np.array(v) if isinstance(v, list) else v for f, v in d.items()}
        for k, d in tasks.items()
    }


# ── Análise ───────────────────────────────────────────────────────────────────


def analyze(tasks: dict) -> dict:
    results = {}
    for name, d in tasks.items():
        period_ns = d["period_ms"] * 1_000_000
        is_periodic = d["period_ms"] > 0
        jitter_us = (d["actual"] - d["scheduled"]) / 1e3
        exec_time_us = (d["exec_end"] - d["actual"]) / 1e3
        if is_periodic:
            deadline_ns = d["scheduled"] + period_ns
            slack_us = (deadline_ns - d["exec_end"]) / 1e3
            miss = d["exec_end"] > deadline_ns
        else:
            slack_us = np.zeros(len(d["scheduled"]))
            miss = np.zeros(len(d["scheduled"]), dtype=bool)
        results[name] = {
            "period_ms": d["period_ms"],
            "is_periodic": is_periodic,
            "cycles": d["cycles"],
            "jitter_us": jitter_us,
            "exec_time_us": exec_time_us,
            "slack_us": slack_us,
            "miss": miss,
            "scheduled": d["scheduled"],
            "actual": d["actual"],
            "exec_end": d["exec_end"],
        }
    return results


def print_stats(results: dict) -> None:
    print("\n╔══════════════════════════════════════════════════════════════════╗")
    print("║          Análise de Timing RTOS — Resumo Estatístico            ║")
    print("╚══════════════════════════════════════════════════════════════════╝\n")
    hdr = f"{'Tarefa':<20} {'Período':>8} {'Jitter Max':>12} {'Jitter Méd':>12} {'ExecMax':>10} {'Misses':>8}"
    print(hdr)
    print("─" * len(hdr))

    def _sort_key(item):
        p = item[1]["period_ms"]
        return (p == 0, p)  # periódicas primeiro (por período), event-driven no fim

    for name, r in sorted(results.items(), key=_sort_key):
        e = r["exec_time_us"][1:] if len(r["exec_time_us"]) > 1 else r["exec_time_us"]
        if r["is_periodic"]:
            j = r["jitter_us"][1:]
            misses = int(r["miss"][1:].sum())
            miss_str = f"{'✗ ' + str(misses) if misses else '✓ 0':>8}"
            print(
                f"{name:<20} {r['period_ms']:>7}ms {j.max():>10.1f}µs {j.mean():>10.1f}µs "
                f"{e.max():>8.1f}µs {miss_str}"
            )
        else:
            n_inv = len(e)
            print(
                f"{name:<20} {'evento':>8}   {'—':>10}   {'—':>10}   "
                f"{e.max():>8.1f}µs {'N/A':>8}  ({n_inv} invocações)"
            )
    print()


# ── Gráficos ─────────────────────────────────────────────────────────────────

COLORS = plt.cm.tab10.colors


def plot_jitter(results: dict, ax: plt.Axes) -> None:
    for i, (name, r) in enumerate(results.items()):
        if not r["is_periodic"]:
            continue  # jitter não se aplica a tarefas event-driven (scheduled = actual)
        cyc = r["cycles"][1:]
        jit = r["jitter_us"][1:]
        ax.plot(
            cyc,
            jit,
            label=f"{name} ({r['period_ms']}ms)",
            color=COLORS[i % len(COLORS)],
            linewidth=0.8,
            alpha=0.85,
        )
    ax.axhline(0, color="black", linestyle="--", linewidth=0.6)
    ax.set_xlabel("Número do Ciclo")
    ax.set_ylabel("Jitter (µs)")
    ax.set_title("Jitter de Wakeup por Ciclo  (≈ 0 = sem drift acumulado)")
    ax.legend(fontsize=8, loc="upper right")
    ax.grid(True, alpha=0.25)


def plot_exec(results: dict, ax: plt.Axes) -> None:
    for i, (name, r) in enumerate(results.items()):
        color = COLORS[i % len(COLORS)]
        cyc = r["cycles"][1:] if len(r["cycles"]) > 1 else r["cycles"]
        et = r["exec_time_us"][1:] if len(r["exec_time_us"]) > 1 else r["exec_time_us"]
        if r["is_periodic"]:
            ax.plot(cyc, et, label=f"{name}", color=color, linewidth=0.8, alpha=0.85)
            ax.axhline(
                r["period_ms"] * 1000.0, color=color, linestyle=":", linewidth=0.7
            )
        else:
            # Tarefas event-driven: marcadores maiores, sem linha de deadline
            ax.plot(
                cyc,
                et,
                "o",
                label=f"{name} (evento)",
                color=color,
                markersize=4,
                alpha=0.80,
                markeredgewidth=0,
            )
    ax.set_xlabel("Número do Ciclo / Invocação")
    ax.set_ylabel("Tempo de Execução (µs)")
    ax.set_title(
        "Tempo de Execução  (pontilhado = deadline das periódicas | ○ = event-driven)"
    )
    ax.legend(fontsize=8, loc="upper right")
    ax.grid(True, alpha=0.25)


def plot_gantt(results: dict, ax: plt.Axes, window_ms: float = GANTT_WINDOW_MS) -> None:
    t_start = min(r["actual"][0] for r in results.values())
    # Periódicas primeiro (ordenadas por período), event-driven ao final
    task_names = sorted(
        results.keys(),
        key=lambda n: (results[n]["period_ms"] == 0, results[n]["period_ms"]),
    )

    for yi, name in enumerate(task_names):
        r = results[name]
        color = COLORS[yi % len(COLORS)]
        period_ns = r["period_ms"] * 1_000_000

        start_ms = (r["actual"] - t_start) / 1e6
        end_ms = (r["exec_end"] - t_start) / 1e6
        sched_ms = (r["scheduled"] - t_start) / 1e6
        dl_ms = (r["scheduled"] + period_ns - t_start) / 1e6
        is_miss = r["exec_end"] > r["scheduled"] + period_ns

        # Ciclos que sobrepõem a janela [0, window_ms]
        mask = (start_ms < window_ms) & (end_ms >= 0)

        # Mínimo de visibilidade: 15% do período (periódicas) ou 20ms fixo (event-driven)
        min_exec_ms = r["period_ms"] * 0.15 if r["is_periodic"] else 20.0

        for s, e, sched, dl, miss in zip(
            start_ms[mask], end_ms[mask], sched_ms[mask], dl_ms[mask], is_miss[mask]
        ):
            if r["is_periodic"]:
                # 1. □ Slot alocado pelo escalonador (outline)
                if dl > 0 and sched < window_ms:
                    ax.barh(
                        yi,
                        dl - sched,
                        left=sched,
                        height=0.70,
                        color="none",
                        edgecolor=color,
                        linewidth=2.0,
                        alpha=0.80,
                        zorder=2,
                    )

            # 2. ■ Execução real (mín. 15% do período para periódicas, 20ms para event-driven)
            exec_w = max(e - s, min_exec_ms)
            ax.barh(
                yi,
                exec_w,
                left=s,
                height=0.46,
                color="crimson" if (miss and r["is_periodic"]) else color,
                alpha=0.90,
                edgecolor="white",
                linewidth=0.4,
                zorder=3,
            )

            if r["is_periodic"]:
                # 3. ▼ Seta no deadline
                if 0 <= dl <= window_ms:
                    ax.vlines(
                        dl, yi + 0.35, yi + 0.85, colors=color, linewidth=1.8, zorder=5
                    )
                    ax.plot(
                        dl,
                        yi + 0.35,
                        "v",
                        color=color,
                        markersize=9,
                        zorder=6,
                        clip_on=True,
                    )

    ax.set_yticks(range(len(task_names)))
    ax.set_yticklabels(task_names)
    ax.set_xlim(0, window_ms)
    ax.set_xlabel("Tempo (ms)")
    ax.set_title(
        f"Gantt — primeiros {window_ms} ms\n"
        f"□ slot alocado  |  ■ execução (mín. 15%*)  |  ▼ deadline  |  sem □▼ = event-driven\n"
        f"*barras de execução não estão em escala real (execuções reais: µs)"
    )
    ax.grid(True, axis="x", alpha=0.25)


# ── Entry point ───────────────────────────────────────────────────────────────


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else LOG_PATH
    if not path.exists():
        print(f"Arquivo não encontrado: {path}")
        print("Execute o sistema primeiro para gerar dados de timing.")
        sys.exit(1)

    print(f"Carregando: {path}")
    tasks = load(path)
    if not tasks:
        print("Nenhum dado encontrado.")
        sys.exit(1)

    results = analyze(tasks)
    print_stats(results)

    fig, axes = plt.subplots(3, 1, figsize=(14, 12))
    fig.suptitle(
        "Análise de Timing RTOS — Prova de Cumprimento de Deadlines",
        fontsize=13,
        fontweight="bold",
    )

    plot_jitter(results, axes[0])
    plot_exec(results, axes[1])
    plot_gantt(results, axes[2])

    plt.tight_layout()

    out = path.parent / "timing_analysis.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    print(f"Gráfico salvo em: {out}")
    plt.show()


if __name__ == "__main__":
    main()
