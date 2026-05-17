/**
 * @file SurfaceReconstruction.cpp
 * @brief Implementação da simulação do LIDAR de teto.
 */
#include "tasks/SurfaceReconstruction.hpp"

#include <chrono>
#include <cmath>
#include <random>
#include <thread>

#include "core/TerminalPrinter.hpp"

namespace tasks {

/**
 * @brief Construtor da tarefa de reconstrução de superfície.
 */
SurfaceReconstruction::SurfaceReconstruction(
    std::shared_ptr<core::ThreadSafeQueue<core::SurfaceData>> buffer,
    std::shared_ptr<core::SharedContext> context, double threshold)
    : surface_buffer_(buffer), context_(context), threshold_anomaly_(threshold) {}

/**
 * @brief Executa o loop principal de varredura (LIDAR).
 * @details O LIDAR apenas consome a odometria publicada pelo Encoder.
 * Não tem acoplamento com a velocidade do motor ou planta física.
 */
void SurfaceReconstruction::run() {
    auto proximo_ciclo = std::chrono::steady_clock::now();
    const auto periodo = std::chrono::milliseconds(100);  // LIDAR varre a 10Hz

    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_real_distribution<> prob_dist(0.0, 1.0);
    std::uniform_real_distribution<> size_dist(0.5, 2.0);

    bool inside_anomaly = false;
    double anomaly_end_x = 0.0;
    double current_anomaly_y = 2.0;

    while (context_->is_running) {
        proximo_ciclo += periodo;

        // 1. Consome Odometria do "Broker" (/sensor/odometria)
        double current_x = context_->current_odometry.load();

        // 2. Faz a varredura a laser simulada
        double simulated_lidar_y = 2.0;

        if (!inside_anomaly && prob_dist(gen) < 0.03) {
            inside_anomaly = true;
            anomaly_end_x = current_x + size_dist(gen);

            if (prob_dist(gen) > 0.5) {
                current_anomaly_y = 2.0 + (prob_dist(gen) * 2.0);
            } else {
                current_anomaly_y = 2.0 - (prob_dist(gen) * 1.0);
            }
        }

        if (inside_anomaly) {
            if (current_x < anomaly_end_x) {
                simulated_lidar_y = current_anomaly_y;
            } else {
                inside_anomaly = false;
                simulated_lidar_y = 2.0;
            }
        }

        // Análise contínua do perfil do teto
        double variacao = std::abs(simulated_lidar_y - 2.0);
        double limite_variacao = std::abs(threshold_anomaly_ - 2.0);

        if (variacao >= limite_variacao) {
            if (!context_->isAnomalyActive()) {
                core::TerminalPrinter::Log(core::TerminalPrinter::Level::Warning, "Sensor LIDAR",
                                           "ALERTA: Variação estrutural (" +
                                               std::to_string(simulated_lidar_y) +
                                               "m)! Disparando flag global.");
                context_->triggerAnomaly();
            }
        } else {
            if (context_->isAnomalyActive()) {
                core::TerminalPrinter::Log(core::TerminalPrinter::Level::Info, "Sensor LIDAR",
                                           "Superfície normalizada. Desativando flag.");
                context_->resetAnomaly();
            }
        }

        // 3. Monta o pacote de dados fundindo LIDAR + Odometria
        core::SurfaceData data{
            static_cast<uint64_t>(std::chrono::system_clock::now().time_since_epoch().count()),
            current_x, simulated_lidar_y, 0.98};

        if (!surface_buffer_->push(data)) {
            break;
        }

        std::this_thread::sleep_until(proximo_ciclo);
    }
}

}  // namespace tasks
