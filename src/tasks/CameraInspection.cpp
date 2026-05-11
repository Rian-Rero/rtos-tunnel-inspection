/**
 * @file CameraInspection.cpp
 * @brief Implementacao da tarefa de inspecao detalhada com camera.
 */
#include "tasks/CameraInspection.hpp"

#include <chrono>
#include <thread>

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
    while (context_->is_running) {
        // Fica bloqueada aqui (sleeping) até a anomalia ser detectada
        context_->waitForAnomaly();

        if (!context_->is_running)
            break;

        core::TerminalPrinter::Log(core::TerminalPrinter::Level::Info, "Camera",
                                   "Iniciando inspecao detalhada (carga pesada)...");

        // Emulação de processamento pesado (Na Etapa 2, chamará o YOLO via system() ou IPC)
        auto start = std::chrono::high_resolution_clock::now();
        while (std::chrono::duration_cast<std::chrono::milliseconds>(
                   std::chrono::high_resolution_clock::now() - start)
                   .count() < 1500) {
            // Busy wait simulando uso de CPU
        }

        core::TerminalPrinter::Log(core::TerminalPrinter::Level::Success, "Camera",
                                   "Inspecao concluida. Retornando ao modo normal.");
        context_->resetAnomaly();
    }
}

}  // namespace tasks