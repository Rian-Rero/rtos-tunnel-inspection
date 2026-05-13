/**
 * @file main.cpp
 * @brief Ponto de entrada do sistema de inspeção ATR.
 */
#include <atomic>
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

/** * @brief Flag atômica exclusiva para o Signal Handler se comunicar com a thread principal.
 */
std::atomic<bool> global_shutdown_requested{false};

/**
 * @brief Handler para encerramento seguro via sinal do sistema (CTRL+C ou SIGTERM).
 * @param signum Número do sinal recebido.
 */
void signalHandler(int signum) {
    core::TerminalPrinter::Log(core::TerminalPrinter::Level::Warning, "Sistema",
                               "Sinal de sistema (" + std::to_string(signum) +
                                   ") recebido. Solicitando shutdown gracioso...");
    global_shutdown_requested = true;
}

/**
 * @brief Função principal do sistema.
 * @return Código de status de encerramento.
 */
int main() {
    // Registro dos tratadores de sinal
    std::signal(SIGINT, signalHandler);
    std::signal(SIGTERM, signalHandler);

    core::TerminalPrinter::Banner("Sistema de Inspeção ATR", "Etapa 1 - Inicialização");

    // Instanciação isolada de contextos e buffers
    auto global_context = std::make_shared<core::SharedContext>();
    auto command_buffer = std::make_shared<core::ThreadSafeQueue<core::NavigationSetpoint>>();
    auto surface_buffer = std::make_shared<core::ThreadSafeQueue<core::SurfaceData>>();

    // Instanciação das Tarefas
    // Threshold de 2.8m (ou seja, 0.8m de variação aceitável sobre o teto base que é 2.0m)
    auto task_reconstruction =
        std::make_shared<tasks::SurfaceReconstruction>(surface_buffer, global_context, 2.8);
    auto task_camera = std::make_shared<tasks::CameraInspection>(global_context);
    auto task_nav_cmd = std::make_shared<tasks::NavigationCommand>(global_context, command_buffer);
    auto task_nav_ctrl = std::make_shared<tasks::NavigationControl>(global_context, command_buffer);
    auto task_dist_calc = std::make_shared<tasks::DistanceCalculator>(global_context);
    auto task_collector = std::make_shared<tasks::DataCollector>(surface_buffer, global_context,
                                                                 "inspection_log.csv");

    // Lançamento das Threads
    std::vector<std::thread> thread_pool;
    thread_pool.emplace_back([task_reconstruction]() { task_reconstruction->run(); });
    thread_pool.emplace_back([task_camera]() { task_camera->run(); });
    thread_pool.emplace_back([task_nav_cmd]() { task_nav_cmd->run(); });
    thread_pool.emplace_back([task_nav_ctrl]() { task_nav_ctrl->run(); });
    thread_pool.emplace_back([task_dist_calc]() { task_dist_calc->run(); });
    thread_pool.emplace_back([task_collector]() { task_collector->run(); });

    // A thread principal atua como Watchdog. Dorme até que um CTRL+C seja pressionado.
    while (!global_shutdown_requested) {
        std::this_thread::sleep_for(std::chrono::milliseconds(200));
    }

    core::TerminalPrinter::Log(core::TerminalPrinter::Level::Info, "Sistema",
                               "Encerrando buffers e notificando tarefas...");

    // Inicia o shutdown coordenado da arquitetura
    global_context->is_running = false;
    command_buffer->close();
    surface_buffer->close();

    // Libera a thread de câmera caso ela esteja presa esperando anomalia no Condition Variable
    global_context->triggerAnomaly();

    // Aguarda o encerramento limpo (join) de todas as threads operárias
    for (auto& t : thread_pool) {
        if (t.joinable()) {
            t.join();
        }
    }

    core::TerminalPrinter::Log(core::TerminalPrinter::Level::Success, "Sistema",
                               "Sistema encerrado sem vazamento de memória.");
    return 0;
}