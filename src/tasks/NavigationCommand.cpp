#include "tasks/NavigationCommand.hpp"
#include <chrono>
#include <iostream>
#include <thread>

namespace tasks {

NavigationCommand::NavigationCommand(std::shared_ptr<core::SharedContext> ctx, 
                                     std::shared_ptr<core::ThreadSafeQueue<core::NavigationSetpoint>> queue)
    : context_(ctx), cmd_queue_(queue) {}

void NavigationCommand::run() {
    // Define o ponto de partida do relógio monotônico
    auto next_wakeup = std::chrono::steady_clock::now();
    const auto cycle_time = std::chrono::milliseconds(80);

    while (context_->is_running) {
        // Atualiza o instante do próximo despertar antes de rodar a lógica
        next_wakeup += cycle_time;

        core::NavigationSetpoint sp;
        
        if (context_->isAnomalyActive()) {
            sp.speed_setpoint = 15; 
            sp.is_automatic = true;
        } else {
            sp.speed_setpoint = 50; 
            sp.is_automatic = true;
        }

        // Operação IPC de escrita (não bloqueante se a fila não estiver cheia)
        cmd_queue_->push(sp);

        // Suspensão da thread até o tempo exato calculado, descontando o tempo de processamento
        std::this_thread::sleep_until(next_wakeup); 
    }
}

} // namespace tasks