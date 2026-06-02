/**
 * @file NavigationCommand.cpp
 * @brief Implementação da tarefa de geração de comandos de navegação.
 */
#include "tasks/NavigationCommand.hpp"

#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <thread>

namespace tasks {

/**
 * @brief Construtor da tarefa NavigationCommand.
 * @param ctx Ponteiro compartilhado para o contexto global.
 * @param queue Ponteiro compartilhado para a fila de setpoints.
 */
NavigationCommand::NavigationCommand(
    std::shared_ptr<core::SharedContext> ctx,
    std::shared_ptr<core::ThreadSafeQueue<core::NavigationSetpoint>> queue)
    : context_(ctx), cmd_queue_(queue) {}

/**
 * @brief Executa o loop principal da tarefa.
 */
void NavigationCommand::run() {
    // Define o ponto de partida do relógio monotônico
    auto next_wakeup = std::chrono::steady_clock::now();
    const auto cycle_time = std::chrono::milliseconds(80);

    while (context_->is_running) {
        // Atualiza o instante do próximo despertar antes de rodar a lógica
        next_wakeup += cycle_time;

        core::NavigationSetpoint sp;

        if (context_->manual_mode.load()) {
            const int speed = std::clamp(std::abs(context_->speed_setpoint.load()), 0, 100);
            const int direction = std::clamp(context_->direction.load(), -1, 1);
            sp.speed_setpoint = direction * speed;
            sp.is_automatic = false;
        } else if (context_->isAnomalyActive()) {
            sp.speed_setpoint = 15;
            sp.is_automatic = true;
        } else {
            sp.speed_setpoint = 50;
            sp.is_automatic = true;
        }

        // Operação IPC de escrita (não bloqueante se a fila não estiver cheia)
        if (!cmd_queue_->push(sp)) {
            break;
        }

        // Suspensão da thread até o tempo exato calculado, descontando o tempo de processamento
        std::this_thread::sleep_until(next_wakeup);
    }
}

}  // namespace tasks
