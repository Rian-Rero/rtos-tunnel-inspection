/**
 * @file DistanceCalculator.cpp
 * @brief Implementação da tarefa de cálculo de distância.
 */
#include "tasks/DistanceCalculator.hpp"

#include <chrono>
#include <string>
#include <thread>

#include "core/TerminalPrinter.hpp"

namespace tasks {

/**
 * @brief Construtor da tarefa DistanceCalculator.
 * @param ctx Ponteiro compartilhado para o contexto global.
 */
DistanceCalculator::DistanceCalculator(std::shared_ptr<core::SharedContext> ctx)
    : context_(ctx), total_distance_(0.0), last_encoder_state_(false) {}

/**
 * @brief Executa o loop principal da tarefa.
 */
void DistanceCalculator::run() {
    int sim_counter = 0;

    auto next_wakeup = std::chrono::steady_clock::now();
    const auto cycle_time = std::chrono::milliseconds(20);

    while (context_->is_running) {
        next_wakeup += cycle_time;

        sim_counter++;
        bool current_encoder_state = last_encoder_state_;

        // Simulação do sinal do encoder (troca a cada 50 ciclos = 1 segundo)
        if (sim_counter >= 50) {
            current_encoder_state = !last_encoder_state_;
            sim_counter = 0;
        }

        if (current_encoder_state != last_encoder_state_) {
            total_distance_ += 1.0;
            core::TerminalPrinter::Log(
                core::TerminalPrinter::Level::Info, "Encoder",
                "Odometria atualizada: " + std::to_string(total_distance_) + "m");
        }

        last_encoder_state_ = current_encoder_state;

        std::this_thread::sleep_until(next_wakeup);
    }
}

/**
 * @brief Retorna a distância total acumulada.
 * @return Distância total em metros.
 */
double DistanceCalculator::getTotalDistance() const { return total_distance_; }

}  // namespace tasks