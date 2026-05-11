/**
 * @file CameraInspection.cpp
 * @brief Implementação da tarefa de inspeção detalhada com câmera.
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

        core::TerminalPrinter::Log(core::TerminalPrinter::Level::Info, "Câmera",
                                   "Iniciando inspeção detalhada (carga pesada)...");

        // Emulação de processamento pesado (na Etapa 2, chamará o YOLO via system() ou IPC)
        auto start = std::chrono::high_resolution_clock::now();
        while (std::chrono::duration_cast<std::chrono::milliseconds>(
                   std::chrono::high_resolution_clock::now() - start)
                   .count() < 1500) {
            // Busy wait simulando uso de CPU
        }

        core::TerminalPrinter::Log(core::TerminalPrinter::Level::Success, "Câmera",
                                   "Inspeção concluída. Retornando ao modo normal.");
        context_->resetAnomaly();
    }
}

}  // namespace tasks