/**
 * @file DistanceCalculator.cpp
 * @brief Implementação da tarefa de cálculo de distância (Simulação de Encoder).
 */
#include "tasks/DistanceCalculator.hpp"

#include <chrono>
#include <string>
#include <thread>

#include "core/TerminalPrinter.hpp"

namespace tasks {

/**
 * @brief Construtor da tarefa DistanceCalculator.
 * @param ctx Ponteiro compartilhado para o contexto global (Broker).
 */
DistanceCalculator::DistanceCalculator(std::shared_ptr<core::SharedContext> ctx)
    : context_(ctx), total_distance_(0.0), last_encoder_state_(false) {}

/**
 * @brief Executa o loop principal da tarefa atuando como um driver de Encoder real.
 * @details Lê a velocidade física do eixo, converte para ticks de encoder
 * dependendo da circunferência da roda, calcula a odometria e publica no broker.
 */
void DistanceCalculator::run() {
    auto next_wakeup = std::chrono::steady_clock::now();
    const auto cycle_time = std::chrono::milliseconds(20);  // Lê o sensor a 50Hz

    // Parâmetros físicos simulados do robô
    const double wheel_circumference = 0.5;  // Roda de 50cm de circunferência
    const double ticks_per_rev = 1024.0;     // Resolução do encoder (1024 PPR)
    double simulated_ticks = 0.0;

    int log_divider = 0;

    while (context_->is_running) {
        next_wakeup += cycle_time;

        // 1. Lê o giro real do motor (Simulado pela planta via SharedContext)
        double speed_percent = context_->current_speed.load();
        double speed_ms = (speed_percent / 100.0) * 2.0;  // Assume 100% = 2.0 m/s

        // 2. Calcula delta físico e gera "ticks" de hardware virtual
        double delta_dist = speed_ms * 0.020;  // d = v * t (t = 20ms)
        total_distance_ += delta_dist;
        if (total_distance_ < 0.0) {
            total_distance_ = 0.0;
        }

        // 3. O driver processa os ticks e atualiza a odometria do sistema
        simulated_ticks = (total_distance_ / wheel_circumference) * ticks_per_rev;

        // 4. Publica a odometria para o restante do robô (Tópico: /sensor/odometria)
        context_->current_odometry.store(total_distance_);

        // Imprime log a cada 1 segundo (50 ciclos de 20ms)
        if (++log_divider >= 50) {
            core::TerminalPrinter::Log(core::TerminalPrinter::Level::Info, "Encoder",
                                       "Odometria: " + std::to_string(total_distance_) + "m (" +
                                           std::to_string(static_cast<int>(simulated_ticks)) +
                                           " ticks lidos)");
            log_divider = 0;
        }

        std::this_thread::sleep_until(next_wakeup);
    }
}

/**
 * @brief Retorna a distância total acumulada.
 */
double DistanceCalculator::getTotalDistance() const { return total_distance_; }

}  // namespace tasks
