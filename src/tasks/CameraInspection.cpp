/**
 * @file CameraInspection.cpp
 * @brief Implementação da tarefa de inspeção detalhada com câmera.
 */
#include "tasks/CameraInspection.hpp"

#include <chrono>
#include <thread>

#include "core/MqttPublisher.hpp"
#include "core/TaskTimingLogger.hpp"
#include "core/TerminalPrinter.hpp"

namespace tasks {

/**
 * @brief Construtor da tarefa CameraInspection.
 * @param context Ponteiro compartilhado para o contexto global.
 */
CameraInspection::CameraInspection(std::shared_ptr<core::SharedContext> context)
    : context_(context) {}

/**
 * @brief Executa o loop principal da tarefa.
 */
void CameraInspection::run() {
    core::MqttPublisher camera_cmd_pub("cmd/camera");
    core::MqttPublisher inspection_state_pub("state/inspection");
    uint64_t invocation_num = 0;

    while (context_->is_running) {
        // Fica bloqueada aqui (sleeping) até a anomalia ser detectada
        context_->waitForAnomaly();

        if (!context_->is_running)
            break;

        auto actual = std::chrono::steady_clock::now();

        core::TerminalPrinter::Log(core::TerminalPrinter::Level::Info, "Câmera",
                                   "Iniciando inspeção detalhada (carga pesada)...");
        inspection_state_pub.publish("1");
        camera_cmd_pub.publish("1");

        // Mantém a tarefa C++ ocupada enquanto o serviço YOLO processa o gatilho via MQTT.
        auto start = std::chrono::high_resolution_clock::now();
        while (std::chrono::duration_cast<std::chrono::milliseconds>(
                   std::chrono::high_resolution_clock::now() - start)
                   .count() < 1500) {
            // Busy wait simulando uso de CPU
        }
        core::TaskTimingLogger::instance().log(
            {"CameraYOLO", 0, invocation_num++, core::TaskTimingLogger::toNs(actual),
             core::TaskTimingLogger::toNs(actual),
             core::TaskTimingLogger::toNs(std::chrono::steady_clock::now())});

        camera_cmd_pub.publish("0");
        inspection_state_pub.publish("0");

        core::TerminalPrinter::Log(core::TerminalPrinter::Level::Success, "Câmera",
                                   "Inspeção concluída. Retornando ao modo normal.");

        while (context_->is_running && context_->isAnomalyActive()) {
            std::this_thread::sleep_for(std::chrono::milliseconds(50));
        }
    }
}

}  // namespace tasks
