/**
 * @file main.cpp
 * @brief Ponto de entrada do sistema de inspeção ATR.
 */
#include <csignal>
#include <memory>
#include <string>
#include <thread>
#include <vector>

#include "core/DataTypes.hpp"
#include "core/SharedContext.hpp"
#include "core/TerminalPrinter.hpp"
#include "core/ThreadSafeQueue.hpp"
#include "tasks/CameraInspection.hpp"
#include "tasks/DataCollector.hpp"
#include "tasks/DistanceCalculator.hpp"
#include "tasks/NavigationCommand.hpp"
#include "tasks/NavigationControl.hpp"
#include "tasks/SurfaceReconstruction.hpp"

std::shared_ptr<core::SharedContext> global_context = std::make_shared<core::SharedContext>();
std::shared_ptr<core::ThreadSafeQueue<core::NavigationSetpoint>> global_command_buffer;
std::shared_ptr<core::ThreadSafeQueue<core::SurfaceData>> global_surface_buffer;

/**
 * @brief Handler para encerramento seguro via sinal do sistema.
 * @param signum Número do sinal recebido.
 */
void signalHandler(int signum) {
    core::TerminalPrinter::Log(
        core::TerminalPrinter::Level::Warning, "Sistema",
        "Encerrando o sistema ordenadamente (" + std::to_string(signum) + ")...");
    global_context->is_running = false;
    global_context->triggerAnomaly();
    if (global_command_buffer) {
        global_command_buffer->close();
    }
    if (global_surface_buffer) {
        global_surface_buffer->close();
    }
}

/**
 * @brief Função principal do sistema.
 * @return Código de status de encerramento.
 */
int main() {
    std::signal(SIGINT, signalHandler);
    core::TerminalPrinter::Banner("Sistema de Inspeção ATR", "Etapa 1 - Inicialização");

    // Instanciação dos Buffers
    auto command_buffer = std::make_shared<core::ThreadSafeQueue<core::NavigationSetpoint>>();
    auto surface_buffer = std::make_shared<core::ThreadSafeQueue<core::SurfaceData>>();
    global_command_buffer = command_buffer;
    global_surface_buffer = surface_buffer;

    // Instanciação das Tarefas
    auto task_reconstruction =
        std::make_shared<tasks::SurfaceReconstruction>(surface_buffer, global_context, 3.0);
    auto task_camera = std::make_shared<tasks::CameraInspection>(global_context);
    auto task_nav_cmd = std::make_shared<tasks::NavigationCommand>(global_context, command_buffer);
    auto task_nav_ctrl = std::make_shared<tasks::NavigationControl>(global_context, command_buffer);
    auto task_dist_calc = std::make_shared<tasks::DistanceCalculator>(global_context);
    auto task_collector = std::make_shared<tasks::DataCollector>(surface_buffer, global_context);

    // Lançamento das Threads
    std::vector<std::thread> thread_pool;
    thread_pool.emplace_back([task_reconstruction]() { task_reconstruction->run(); });
    thread_pool.emplace_back([task_camera]() { task_camera->run(); });
    thread_pool.emplace_back([task_nav_cmd]() { task_nav_cmd->run(); });
    thread_pool.emplace_back([task_nav_ctrl]() { task_nav_ctrl->run(); });
    thread_pool.emplace_back([task_dist_calc]() { task_dist_calc->run(); });
    thread_pool.emplace_back([task_collector]() { task_collector->run(); });

    // Aguardar encerramento
    for (auto& t : thread_pool) {
        if (t.joinable()) {
            t.join();
        }
    }

    core::TerminalPrinter::Log(core::TerminalPrinter::Level::Success, "Sistema",
                               "Sistema encerrado.");
    return 0;
}