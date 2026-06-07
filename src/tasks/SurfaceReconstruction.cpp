/**
 * @file SurfaceReconstruction.cpp
 * @brief Implementação da simulação do LIDAR de teto.
 */
#include "tasks/SurfaceReconstruction.hpp"

#include <chrono>
#include <cmath>
#include <cstdint>
#include <limits>
#include <thread>

#include "core/TaskTimingLogger.hpp"
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

// Gera anomalias estruturais pseudo-aleatórias distribuídas ao longo de toda a exploração.
// Determinístico: dado x, sempre retorna o mesmo offset (terreno consistente).
// O robô não conhece previamente — descobre apenas pela leitura do LIDAR.
double structuralAnomalyOffset(double x) {
    if (x < 2.0)
        return 0.0;  // zona de entrada livre

    // Blocos de 3m; cada bloco pode conter uma anomalia independente.
    const double BLOCK_SIZE = 3.0;
    const int block_idx = static_cast<int>(x / BLOCK_SIZE);

    // Hash LCG determinístico para o bloco atual
    uint32_t h = static_cast<uint32_t>(block_idx + 1);
    h = h * 1664525u + 1013904223u;
    h = h * 22695477u + 12345678u;
    h = h * 134775813u + 1u;

    // 55% de chance de não ter anomalia neste bloco
    if ((h & 0xFF) < 140)
        return 0.0;

    h = h * 1664525u + 1013904223u;

    // Largura da anomalia: 0.8 m a 1.6 m
    const double width = 0.8 + ((h & 0xFF) / 255.0) * 0.8;

    h = h * 22695477u + 12345678u;

    // Início da anomalia dentro do bloco (com margem nas bordas)
    const double margin = 0.3;
    const double start_local = margin + ((h & 0xFF) / 255.0) * (BLOCK_SIZE - width - 2.0 * margin);
    const double anom_start = block_idx * BLOCK_SIZE + start_local;
    const double anom_end = anom_start + width;

    if (x < anom_start || x > anom_end)
        return 0.0;

    h = h * 134775813u + 1u;

    // Tipo e magnitude: buraco (offset positivo) ou saliência (offset negativo)
    const bool is_buraco = ((h >> 8) & 0x1) == 0;

    h = h * 1664525u + 1013904223u;
    const double frac = (h & 0xFF) / 255.0;

    return is_buraco ? (0.60 + frac * 0.55)    // Buraco: +0.60 m a +1.15 m
                     : -(0.45 + frac * 0.35);  // Saliência: -0.45 m a -0.80 m
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
    uint64_t cycle_num = 0;

    while (context_->is_running) {
        auto scheduled = proximo_ciclo;
        auto actual = std::chrono::steady_clock::now();
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
            core::TaskTimingLogger::instance().log(
                {"SurfaceRecon", 100, cycle_num++, core::TaskTimingLogger::toNs(scheduled),
                 core::TaskTimingLogger::toNs(actual),
                 core::TaskTimingLogger::toNs(std::chrono::steady_clock::now())});
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

        core::TaskTimingLogger::instance().log(
            {"SurfaceRecon", 100, cycle_num++, core::TaskTimingLogger::toNs(scheduled),
             core::TaskTimingLogger::toNs(actual),
             core::TaskTimingLogger::toNs(std::chrono::steady_clock::now())});

        std::this_thread::sleep_until(proximo_ciclo);
    }
}

}  // namespace tasks
