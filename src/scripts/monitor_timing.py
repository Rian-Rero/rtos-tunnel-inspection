#!/usr/bin/env python3
"""
Monitor de timing RTOS em tempo real.

Usa plt.ion() + plt.pause() — mais confiável que FuncAnimation quando
rodado como subprocess. Atualiza a cada 500 ms.

Uso:
    python monitor_timing.py [caminho_do_csv]
"""

import signal
import sys
from collections import defaultdict
from functools import reduce
from math import gcd
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

LOG_PATH = Path("data/logs/task_timing.csv")
UPDATE_S = 0.5  # intervalo de redesenho (segundos)
MAX_CYCLES = 300  # ciclos visíveis nos gráficos de série temporal

COLORS = plt.cm.tab10.colors
MIN_EXEC_FRACTION = 0.15


def _lcm(a: int, b: int) -> int:
    return a * b // gcd(a, b)


def _hyperperiod_ms(tasks: dict) -> float:
    periods = [d["period_ms"] for d in tasks.values() if d["period_ms"] > 0]
    return float(reduce(_lcm, periods)) if periods else 100.0


def _middle_hyperperiod_window(tasks: dict, window_ms: float) -> int:
    """Retorna o início de um hiperperíodo completo no meio da amostra atual."""
    window_ns = int(window_ms * 1_000_000)
    periodic = [d for d in tasks.values() if d["period_ms"] > 0]
    t_all_start = min(d["actual"][0] for d in tasks.values())
    t_all_end = max(d["exec_end"][-1] for d in tasks.values())
    t_mid = (t_all_start + t_all_end) // 2

    if not periodic or t_all_end - t_all_start <= window_ns:
        return max(t_all_start, t_mid - window_ns // 2)

    anchor = min(d["scheduled"][0] for d in periodic)
    first_k = max(0, (t_all_start - anchor + window_ns - 1) // window_ns)
    last_k = (t_all_end - anchor - window_ns) // window_ns

    if last_k >= first_k:
        target_k = round((t_mid - anchor - window_ns // 2) / window_ns)
        k = min(max(target_k, first_k), last_k)
        return anchor + k * window_ns

    return min(max(t_mid - window_ns // 2, t_all_start), t_all_end - window_ns)


# ── Leitura incremental ───────────────────────────────────────────────────────
# Lemos linha a linha e só avançamos o ponteiro em linhas completamente escritas
# (6 campos). Isso evita parsear uma linha que o C++ ainda está escrevendo.

_file_pos: int = 0
_tasks_raw: dict = defaultdict(
    lambda: {
        "period_ms": 0,
        "cycles": [],
        "scheduled": [],
        "actual": [],
        "exec_end": [],
    }
)


def _load_new_rows(path: Path) -> None:
    global _file_pos
    try:
        with open(path, newline="") as f:
            if _file_pos == 0:
                f.readline()  # descarta cabeçalho
                _file_pos = f.tell()
            f.seek(_file_pos)

            last_good = _file_pos
            for raw_line in f:
                parts = raw_line.strip().split(",")
                if len(parts) != 6:
                    continue  # linha incompleta — não avança ponteiro
                try:
                    name, period_ms, cycle_num, sched, actual, exec_end = parts
                    d = _tasks_raw[name]
                    d["period_ms"] = int(period_ms)
                    d["cycles"].append(int(cycle_num))
                    d["scheduled"].append(int(sched))
                    d["actual"].append(int(actual))
                    d["exec_end"].append(int(exec_end))
                    last_good = f.tell()
                except ValueError:
                    continue
            _file_pos = last_good
    except FileNotFoundError:
        pass


def _snapshot() -> dict:
    """Converte _tasks_raw em arrays numpy (cópia point-in-time)."""
    out = {}
    for name, d in _tasks_raw.items():
        min_samples = 1 if d["period_ms"] == 0 else 2
        if len(d["cycles"]) < min_samples:
            continue
        out[name] = {
            "period_ms": d["period_ms"],
            "cycles": np.array(d["cycles"], dtype=np.int64),
            "scheduled": np.array(d["scheduled"], dtype=np.int64),
            "actual": np.array(d["actual"], dtype=np.int64),
            "exec_end": np.array(d["exec_end"], dtype=np.int64),
        }
    return out


# ── Desenho de cada painel ────────────────────────────────────────────────────


def _draw_jitter(ax: plt.Axes, tasks: dict) -> None:
    ax.cla()
    for i, (name, d) in enumerate(tasks.items()):
        if d["period_ms"] == 0:
            continue  # jitter não se aplica a tarefas event-driven
        cyc = d["cycles"][1:][-MAX_CYCLES:]
        jit = ((d["actual"] - d["scheduled"]) / 1e3)[1:][-MAX_CYCLES:]
        ax.plot(
            cyc,
            jit,
            label=f"{name} ({d['period_ms']}ms)",
            color=COLORS[i % len(COLORS)],
            linewidth=0.8,
            alpha=0.85,
        )
    ax.axhline(0, color="black", linestyle="--", linewidth=0.6)
    ax.set_ylabel("Jitter (µs)")
    ax.set_title(f"Jitter de Wakeup  (últimos {MAX_CYCLES} ciclos — ≈ 0 = sem drift)")
    ax.legend(fontsize=8, loc="upper right")
    ax.grid(True, alpha=0.25)


def _draw_exec(ax: plt.Axes, tasks: dict) -> None:
    ax.cla()
    for i, (name, d) in enumerate(tasks.items()):
        color = COLORS[i % len(COLORS)]
        cyc = d["cycles"][1:][-MAX_CYCLES:]
        et = ((d["exec_end"] - d["actual"]) / 1e3)[1:][-MAX_CYCLES:]
        if d["period_ms"] > 0:
            miss = (d["exec_end"] > d["scheduled"] + d["period_ms"] * 1_000_000)[1:][
                -MAX_CYCLES:
            ]
            ax.plot(
                cyc[~miss],
                et[~miss],
                ".",
                markersize=3,
                color=color,
                label=name,
                alpha=0.75,
            )
            if miss.any():
                ax.plot(cyc[miss], et[miss], "x", markersize=6, color="red", alpha=0.9)
            ax.axhline(
                d["period_ms"] * 1000.0, color=color, linestyle=":", linewidth=0.7
            )
        else:
            # Event-driven: marcadores maiores, sem deadline
            ax.plot(
                cyc,
                et,
                "o",
                markersize=4,
                color=color,
                label=f"{name} (evento)",
                alpha=0.80,
                markeredgewidth=0,
            )
    ax.set_ylabel("Exec (µs)")
    ax.set_title("Tempo de Execução  (pontilhado = deadline | ✗ miss | ○ event-driven)")
    ax.legend(fontsize=8, loc="upper right")
    ax.grid(True, alpha=0.25)


def _draw_gantt(ax: plt.Axes, tasks: dict) -> None:
    ax.cla()
    window_ms = _hyperperiod_ms(tasks)
    # Periódicas primeiro (por período), event-driven ao final
    task_names = sorted(
        tasks.keys(), key=lambda n: (tasks[n]["period_ms"] == 0, tasks[n]["period_ms"])
    )
    if not task_names:
        ax.set_title(f"Gantt — MMC {window_ms:.0f} ms  (aguardando dados...)")
        return

    win_start = _middle_hyperperiod_window(tasks, window_ms)
    t_all_start = min(d["actual"][0] for d in tasks.values())
    win_rel_start_ms = (win_start - t_all_start) / 1e6
    win_rel_end_ms = win_rel_start_ms + window_ms

    for yi, name in enumerate(task_names):
        d = tasks[name]
        color = COLORS[yi % len(COLORS)]
        period_ns = d["period_ms"] * 1_000_000

        is_periodic = d["period_ms"] > 0
        win_end = win_start + int(window_ms * 1_000_000)
        slot_end = d["scheduled"] + period_ns if is_periodic else d["exec_end"]
        mask = (d["scheduled"] < win_end) & (
            np.maximum(d["exec_end"], slot_end) >= win_start
        )
        if not mask.any():
            continue

        s_ms = (d["actual"][mask] - win_start) / 1e6
        e_ms = (d["exec_end"][mask] - win_start) / 1e6
        sched_ms = (d["scheduled"][mask] - win_start) / 1e6
        dl_ms = (d["scheduled"][mask] + period_ns - win_start) / 1e6
        miss = d["exec_end"][mask] > d["scheduled"][mask] + period_ns

        for s, e, sched, dl, is_miss in zip(s_ms, e_ms, sched_ms, dl_ms, miss):
            if is_periodic:
                # 1. □ Retângulo do período — slot alocado pelo escalonador
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
                min_exec_ms = d["period_ms"] * MIN_EXEC_FRACTION if is_periodic else 8.0
                visual_right = min(max(exec_right, exec_left + min_exec_ms), window_ms)
                ax.barh(
                    yi,
                    visual_right - exec_left,
                    left=exec_left,
                    height=0.46,
                    color="crimson" if (is_miss and is_periodic) else color,
                    alpha=0.90,
                    edgecolor="white",
                    linewidth=0.4,
                    zorder=3,
                )

            if is_periodic:
                # 3. ▼ Seta no deadline — linha + triângulo ▼
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
    ax.set_yticklabels(task_names, fontsize=9)
    ax.set_xlim(0, window_ms)
    ax.set_xlabel("Tempo relativo (ms)")
    ax.set_title(
        f"Gantt — hiperperíodo central da amostra (MMC = {window_ms:.0f} ms; "
        f"t={win_rel_start_ms / 1000:.3f}s..{win_rel_end_ms / 1000:.3f}s)\n"
        f"□ slot alocado  |  ■ execução (mín. visual {MIN_EXEC_FRACTION:.0%}; tempo real acima)  |  ▼ deadline"
    )
    ax.grid(True, axis="x", alpha=0.25)


# ── Loop principal ────────────────────────────────────────────────────────────


def _exit_gracefully(signum, frame):
    plt.close("all")
    sys.exit(0)


signal.signal(signal.SIGTERM, _exit_gracefully)


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else LOG_PATH

    plt.ion()
    fig, axes = plt.subplots(3, 1, figsize=(14, 11))
    fig.suptitle("Monitor de Timing RTOS — Tempo Real", fontsize=13, fontweight="bold")
    # tight_layout uma única vez, fora do loop de atualização
    fig.tight_layout(rect=[0, 0.03, 1, 0.97])

    status = fig.text(
        0.5,
        0.005,
        f"Aguardando {path} ...",
        ha="center",
        fontsize=9,
        color="gray",
        style="italic",
    )
    plt.show(block=False)

    try:
        while plt.fignum_exists(fig.number):
            _load_new_rows(path)
            tasks = _snapshot()

            if tasks:
                total = sum(len(d["cycles"]) for d in tasks.values())
                misses = sum(
                    int(
                        (d["exec_end"] > d["scheduled"] + d["period_ms"] * 1_000_000)[
                            1:
                        ].sum()
                    )
                    for d in tasks.values()
                    if d["period_ms"] > 0  # event-driven não tem deadline
                )
                label = f"  ✗ {misses} miss(es)" if misses else "  ✓ sem deadline miss"
                status.set_text(f"{total} ciclos{label}")
                status.set_color("crimson" if misses else "seagreen")

                _draw_jitter(axes[0], tasks)
                _draw_exec(axes[1], tasks)
                _draw_gantt(axes[2], tasks)
            else:
                status.set_text(f"Aguardando {path} ...")
                status.set_color("gray")

            fig.canvas.draw_idle()
            plt.pause(UPDATE_S)

    except (KeyboardInterrupt, SystemExit):
        pass
    except Exception:
        # Janela fechada pelo WM pode lançar TclError/RuntimeError dependendo do backend
        pass
    finally:
        plt.close("all")


if __name__ == "__main__":
    main()
