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
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

LOG_PATH = Path("data/logs/task_timing.csv")
UPDATE_S = 0.5  # intervalo de redesenho (segundos)
GANTT_WINDOW_MS = 300  # janela deslizante do Gantt
MAX_CYCLES = 300  # ciclos visíveis nos gráficos de série temporal

COLORS = plt.cm.tab10.colors

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
        if len(d["cycles"]) < 2:
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
        ax.axhline(d["period_ms"] * 1000.0, color=color, linestyle=":", linewidth=0.7)
    ax.set_ylabel("Exec (µs)")
    ax.set_title("Tempo de Execução  (pontilhado = deadline | ✗ vermelho = miss)")
    ax.legend(fontsize=8, loc="upper right")
    ax.grid(True, alpha=0.25)


def _draw_gantt(ax: plt.Axes, tasks: dict, window_ms: float) -> None:
    ax.cla()
    task_names = sorted(tasks.keys(), key=lambda n: tasks[n]["period_ms"])
    if not task_names:
        ax.set_title(f"Gantt — últimos {window_ms} ms  (aguardando dados...)")
        return

    t_now = max(d["exec_end"][-1] for d in tasks.values())
    win_start = t_now - window_ms * 1_000_000

    for yi, name in enumerate(task_names):
        d = tasks[name]
        color = COLORS[yi % len(COLORS)]
        period_ns = d["period_ms"] * 1_000_000

        # Inclui ciclos que SOBREPÕEM a janela, não só os que começam dentro dela.
        # Garante que a tarefa de 100ms mostre todas as 5 execuções em 500ms.
        mask = d["exec_end"] >= win_start
        if not mask.any():
            continue

        s_ms = (d["actual"][mask] - win_start) / 1e6
        e_ms = (d["exec_end"][mask] - win_start) / 1e6
        sched_ms = (d["scheduled"][mask] - win_start) / 1e6
        dl_ms = (d["scheduled"][mask] + period_ns - win_start) / 1e6
        miss = d["exec_end"][mask] > d["scheduled"][mask] + period_ns

        # Execuções reais são sub-ms (µs). Usamos mínimo proporcional ao
        # período para garantir visibilidade. A barra não está em escala real.
        min_exec_ms = d["period_ms"] * 0.15

        for s, e, sched, dl, is_miss in zip(s_ms, e_ms, sched_ms, dl_ms, miss):
            # 1. □ Retângulo do período — slot alocado pelo escalonador
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

            # 2. ■ Caixa de execução — preenchida, mais estreita que o slot
            #    largura mínima = 15% do período para ser sempre visível
            exec_w = max(e - s, min_exec_ms)
            ax.barh(
                yi,
                exec_w,
                left=s,
                height=0.46,
                color="crimson" if is_miss else color,
                alpha=0.90,
                edgecolor="white",
                linewidth=0.4,
                zorder=3,
            )

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
        f"Gantt — últimos {window_ms} ms\n"
        f"□ slot alocado  |  ■ execução (mín. 15% do período*)  |  ▼ deadline\n"
        f"*barras de execução não estão em escala real (execuções reais: µs)"
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
                )
                label = f"  ✗ {misses} miss(es)" if misses else "  ✓ sem deadline miss"
                status.set_text(f"{total} ciclos{label}")
                status.set_color("crimson" if misses else "seagreen")

                _draw_jitter(axes[0], tasks)
                _draw_exec(axes[1], tasks)
                _draw_gantt(axes[2], tasks, GANTT_WINDOW_MS)
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
