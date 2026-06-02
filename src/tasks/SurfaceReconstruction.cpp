/**
 * @file SurfaceReconstruction.cpp
 * @brief Implementação da simulação do LIDAR de teto.
 */
#include "tasks/SurfaceReconstruction.hpp"

#include <chrono>
#include <cmath>
#include <limits>
#include <thread>

#include "core/TerminalPrinter.hpp"

namespace tasks {

namespace {

constexpr double kNominalCeilingDistanceM = 2.0;
constexpr double kRadiansToDegrees = 57.29577951308232;
constexpr double kMinSurfaceSampleStepM = 0.04;

double floorElevation(double x) { return 0.62 * std::sin(x / 5.4) + 0.16 * std::sin(x / 1.8); }

double floorSlope(double x) {
    return (0.62 / 5.4) * std::cos(x / 5.4) + (0.16 / 1.8) * std::cos(x / 1.8);
}

double naturalCeilingVariation(double x) {
    return 0.06 * std::sin(x / 5.5) + 0.035 * std::sin(x / 1.9);
}

double structuralAnomalyOffset(double x) {
    if (x >= 2.2 && x <= 3.4) {
        return 0.85;  // Buraco no teto: distância medida aumenta.
    }
    if (x >= 6.0 && x <= 7.1) {
        return -0.65;  // Saliência: distância medida diminui.
    }
    if (x >= 10.5 && x <= 12.0) {
        return 1.10;
    }
    return 0.0;
}

double lidarDistanceForPosition(double x) {
    const double floor_y = floorElevation(x);
    const double ceiling_y = floor_y + kNominalCeilingDistanceM + naturalCeilingVariation(x) +
                             structuralAnomalyOffset(x);
    return ceiling_y - floor_y;
}

}  // namespace

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
    double last_sample_x = std::numeric_limits<double>::quiet_NaN();

    while (context_->is_running) {
        proximo_ciclo += periodo;

        // 1. Consome Odometria do "Broker" (/sensor/odometria)
        double current_x = context_->current_odometry.load();

        // 2. Simula um túnel com declive real: a IMU mede o ângulo do piso.
        const double imu_degrees = std::atan(floorSlope(current_x)) * kRadiansToDegrees;
        context_->imu_degrees.store(imu_degrees);

        const double base_lidar_y = kNominalCeilingDistanceM + naturalCeilingVariation(current_x);
        const double simulated_lidar_y = lidarDistanceForPosition(current_x);

        // Análise contínua do perfil do teto
        double variacao = std::abs(simulated_lidar_y - base_lidar_y);
        double limite_variacao = std::abs(threshold_anomaly_ - kNominalCeilingDistanceM);

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
        const bool first_sample = std::isnan(last_sample_x);
        const bool moved_enough = std::abs(current_x - last_sample_x) >= kMinSurfaceSampleStepM;
        if (!first_sample && !moved_enough) {
            std::this_thread::sleep_until(proximo_ciclo);
            continue;
        }

        core::SurfaceData data{
            static_cast<uint64_t>(std::chrono::system_clock::now().time_since_epoch().count()),
            current_x, simulated_lidar_y, 0.98};

        if (!surface_buffer_->push(data)) {
            break;
        }
        last_sample_x = current_x;

        std::this_thread::sleep_until(proximo_ciclo);
    }
}

}  // namespace tasks
