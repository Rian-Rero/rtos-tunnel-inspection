#!/usr/bin/env python3
"""
Analisa os dados de temporização das tarefas periódicas do RTOS e gera:
  - Gráfico de desvio de despertar por ciclo
  - Gráfico de tempo de execução por ciclo (com linha de prazo)
  - Gantt mostrando execução simultânea das tarefas

Uso:
    python analyze_timing.py [caminho_do_csv]

Por padrão lê: data/logs/task_timing.csv
"""

import sys
import csv
from collections import defaultdict
from functools import reduce
from math import gcd
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt


def _lcm(a: int, b: int) -> int:
    """Calcula o mínimo múltiplo comum entre dois períodos."""
    return a * b // gcd(a, b)


def _hyperperiod_ms(records: dict) -> float:
    """Calcula o hiperperíodo das tarefas periódicas, em milissegundos."""
    periods = [
        r["period_ms"]
        for r in records.values()
        if r["is_periodic"] and r["period_ms"] > 0
    ]
    return float(reduce(_lcm, periods)) if periods else 100.0


def _worst_hyperperiod_window(records: dict, window_ms: float) -> int:
    """Retorna o início da janela de hiperperíodo com o pior comportamento de temporização.

    Critério primário: maior número de misses de prazo na janela.
    Critério secundário: maior soma normalizada de tempo de execução (exec/período).
    """
    window_ns = int(window_ms * 1_000_000)
    periodic = [r for r in records.values() if r["is_periodic"]]
    t_all_start = min(r["actual"][0] for r in records.values())
    t_all_end = max(r["exec_end"][-1] for r in records.values())

    if not periodic or t_all_end - t_all_start <= window_ns:
        return max(t_all_start, (t_all_start + t_all_end) // 2 - window_ns // 2)

    anchor = min(r["scheduled"][0] for r in periodic)
    first_k = max(0, (t_all_start - anchor + window_ns - 1) // window_ns)
    last_k = (t_all_end - anchor - window_ns) // window_ns

    if last_k < first_k:
        t_mid = (t_all_start + t_all_end) // 2
        return min(max(t_mid - window_ns // 2, t_all_start), t_all_end - window_ns)

    best_k = first_k
    best_score = (-1, -1.0)

    for k in range(first_k, last_k + 1):
        win_start = anchor + k * window_ns
        win_end = win_start + window_ns

        misses = 0
        exec_score = 0.0
        for r in records.values():
            if not r["is_periodic"]:
                continue
            period_ns = r["period_ms"] * 1_000_000
            in_win = (r["scheduled"] >= win_start) & (r["scheduled"] < win_end)
            deadlines = r["scheduled"][in_win] + period_ns
            exec_ends = r["exec_end"][in_win]
            exec_starts = r["actual"][in_win]
            misses += int(np.sum(exec_ends > deadlines))
            exec_score += float(np.sum((exec_ends - exec_starts) / period_ns))

        score = (misses, exec_score)
        if score > best_score:
            best_score = score
            best_k = k

    return anchor + best_k * window_ns


## Caminho padrão do CSV de temporização gerado pelo núcleo C++.
LOG_PATH = Path("data/logs/task_timing.csv")


# ── Leitura ──────────────────────────────────────────────────────────────────


def load(path: Path) -> dict:
    """Carrega o CSV de temporização e agrupa amostras por tarefa."""
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
            if not all(
                row.get(k) for k in ("actual_ns", "exec_end_ns", "scheduled_ns")
            ):
                continue  # linha incompleta (escrita interrompida pelo Ctrl+C)
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
    """Calcula desvio, tempo de execução, folga e perdas de prazo."""
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
    """Imprime uma tabela textual com estatísticas por tarefa."""
    print("\n╔══════════════════════════════════════════════════════════════════╗")
    print("║       Análise de Temporização RTOS — Resumo Estatístico          ║")
    print("╚══════════════════════════════════════════════════════════════════╝\n")
    hdr = f"{'Tarefa':<20} {'Período':>8} {'Jitter Max':>12} {'Jitter Méd':>12} {'ExecMax':>10} {'Misses':>8}"
    print(hdr)
    print("─" * len(hdr))

    def _sort_key(item):
        """Ordena tarefas periódicas por período e eventos por último."""
        p = item[1]["period_ms"]
        return (p == 0, p)  # periódicas primeiro; orientadas a evento no fim

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

## Paleta de cores usada nos gráficos.
COLORS = plt.cm.tab10.colors
## Fração mínima do período usada para tornar barras curtas visíveis.
MIN_EXEC_FRACTION = 0.15


def plot_jitter(results: dict, ax: plt.Axes) -> None:
    """Plota o desvio entre despertar planejado e real por ciclo."""
    for i, (name, r) in enumerate(results.items()):
        if not r["is_periodic"]:
            continue  # desvio não se aplica a tarefas orientadas a evento
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
    ax.set_ylabel("Desvio (µs)")
    ax.set_title("Desvio de Despertar por Ciclo  (≈ 0 = sem deriva acumulada)")
    ax.legend(fontsize=8, loc="upper right")
    ax.grid(True, alpha=0.25)


def plot_exec(results: dict, ax: plt.Axes) -> None:
    """Plota o tempo de execução de cada tarefa."""
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
            # Tarefas orientadas a evento: marcadores maiores, sem linha de prazo.
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
        "Tempo de Execução  (pontilhado = prazo das periódicas | ○ = orientada a evento)"
    )
    ax.legend(fontsize=8, loc="upper right")
    ax.grid(True, alpha=0.25)


def plot_gantt(results: dict, ax: plt.Axes, window_ms: float = None) -> None:
    """Plota o diagrama de Gantt no pior hiperperíodo da amostra."""
    # Periódicas primeiro (ordenadas por período), orientadas a evento ao final.
    task_names = sorted(
        results.keys(),
        key=lambda n: (results[n]["period_ms"] == 0, results[n]["period_ms"]),
    )

    # Janela = MMC dos períodos das tarefas periódicas (hiperperíodo)
    if window_ms is None:
        window_ms = _hyperperiod_ms(results)

    t_win_start_ns = _worst_hyperperiod_window(results, window_ms)
    t_all_start = min(r["actual"][0] for r in results.values())
    win_rel_start_ms = (t_win_start_ns - t_all_start) / 1e6
    win_rel_end_ms = win_rel_start_ms + window_ms

    for yi, name in enumerate(task_names):
        r = results[name]
        color = COLORS[yi % len(COLORS)]
        period_ns = r["period_ms"] * 1_000_000

        start_ms = (r["actual"] - t_win_start_ns) / 1e6
        end_ms = (r["exec_end"] - t_win_start_ns) / 1e6
        sched_ms = (r["scheduled"] - t_win_start_ns) / 1e6
        dl_ms = (r["scheduled"] + period_ns - t_win_start_ns) / 1e6
        is_miss = r["exec_end"] > r["scheduled"] + period_ns

        # Ciclos/slots que sobrepõem a janela [0, window_ms]
        mask = (sched_ms < window_ms) & (np.maximum(end_ms, dl_ms) >= 0)

        for s, e, sched, dl, miss in zip(
            start_ms[mask], end_ms[mask], sched_ms[mask], dl_ms[mask], is_miss[mask]
        ):
            if r["is_periodic"]:
                # 1. □ Slot alocado pelo escalonador (outline)
                slot_left = max(sched, 0.0)
                slot_right = min(dl, window_ms)
                if slot_right > slot_left:
                    ax.barh(
                        yi,
                        slot_right - slot_left,
                        left=slot_left,
                        height=0.70,
                        color="none",
                        edgecolor=color,
                        linewidth=2.0,
                        alpha=0.80,
                        zorder=2,
                    )

            # 2. ■ Execução real — com largura mínima visual para aparecer no MMC.
            exec_left = max(s, 0.0)
            exec_right = min(e, window_ms)
            if exec_right > exec_left:
                min_exec_ms = (
                    r["period_ms"] * MIN_EXEC_FRACTION if r["is_periodic"] else 8.0
                )
                visual_right = min(max(exec_right, exec_left + min_exec_ms), window_ms)
                ax.barh(
                    yi,
                    visual_right - exec_left,
                    left=exec_left,
                    height=0.46,
                    color="crimson" if (miss and r["is_periodic"]) else color,
                    alpha=0.90,
                    edgecolor="white",
                    linewidth=0.4,
                    zorder=3,
                )

            if r["is_periodic"]:
                # 3. ▼ Seta no prazo.
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
        f"Gantt — PIOR hiperperíodo (MMC = {window_ms:.0f} ms; "
        f"amostra t={win_rel_start_ms / 1000:.3f}s..{win_rel_end_ms / 1000:.3f}s)\n"
        f"□ janela alocada  |  ■ execução (mín. visual {MIN_EXEC_FRACTION:.0%}; tempo real acima)  |  ▼ prazo"
    )
    ax.grid(True, axis="x", alpha=0.25)


# ── Ponto de entrada ──────────────────────────────────────────────────────────


def main() -> None:
    """Executa a análise completa e salva o gráfico final."""
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else LOG_PATH
    if not path.exists():
        print(f"Arquivo não encontrado: {path}")
        print("Execute o sistema primeiro para gerar dados de temporização.")
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
        "Análise de Temporização RTOS — Prova de Cumprimento de Prazos",
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
    if plt.get_backend().lower() != "agg":
        plt.show()


if __name__ == "__main__":
    main()
