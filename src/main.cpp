/**
 * @file main.cpp
 * @brief Ponto de entrada do sistema de inspeção ATR.
 */
#include <pthread.h>
#include <sched.h>
#include <sys/mman.h>

#include <atomic>
#include <csignal>
#include <filesystem>
#include <memory>
#include <string>
#include <thread>
#include <vector>

#include "core/DataTypes.hpp"
#include "core/SharedContext.hpp"
#include "core/TaskTimingLogger.hpp"
#include "core/TerminalPrinter.hpp"
#include "core/ThreadSafeQueue.hpp"
#include "tasks/CameraInspection.hpp"
#include "tasks/DataCollector.hpp"
#include "tasks/DistanceCalculator.hpp"
#include "tasks/MqttBridge.hpp"
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
/**
 * @brief Define política de scheduling SCHED_FIFO para uma thread std::thread.
 * @param t Thread alvo.
 * @param priority Prioridade RT (1=baixa, 99=alta). Rate-Monotonic: período menor = prioridade
 * maior.
 */
static void setThreadRT(std::thread& t, int priority) {
    sched_param param{priority};
    if (pthread_setschedparam(t.native_handle(), SCHED_FIFO, &param) != 0) {
        core::TerminalPrinter::Log(core::TerminalPrinter::Level::Warning, "RT",
                                   "pthread_setschedparam falhou (rode como root para RT real).");
    }
}

int main() {
    // Registro dos tratadores de sinal
    std::signal(SIGINT, signalHandler);
    std::signal(SIGTERM, signalHandler);
#ifdef SIGPIPE
    std::signal(SIGPIPE, SIG_IGN);
#endif

    core::TerminalPrinter::Banner("Sistema de Inspeção ATR", "Etapa 1 - Inicialização");

    // ── Logger de timing: grava ciclo-a-ciclo para análise de jitter/deadline ───
    std::filesystem::create_directories("data/logs");
    core::TaskTimingLogger::instance().open("data/logs/task_timing.csv");

    // Instanciação isolada de contextos e buffers
    auto global_context = std::make_shared<core::SharedContext>();
    auto command_buffer = std::make_shared<core::ThreadSafeQueue<core::NavigationSetpoint>>();
    auto surface_buffer = std::make_shared<core::ThreadSafeQueue<core::SurfaceData>>();

    // Instanciação das Tarefas
    // Threshold de 2.4m (ou seja, 0.4m de variação aceitável sobre o teto base que é 2.0m)
    auto task_reconstruction =
        std::make_shared<tasks::SurfaceReconstruction>(surface_buffer, global_context, 2.4);
    auto task_camera = std::make_shared<tasks::CameraInspection>(global_context);
    auto task_nav_cmd = std::make_shared<tasks::NavigationCommand>(global_context, command_buffer);
    auto task_nav_ctrl = std::make_shared<tasks::NavigationControl>(global_context, command_buffer);
    auto task_dist_calc = std::make_shared<tasks::DistanceCalculator>(global_context);
    auto task_collector = std::make_shared<tasks::DataCollector>(surface_buffer, global_context,
                                                                 "inspection_log.csv");
    auto task_mqtt_bridge = std::make_shared<tasks::MqttBridge>(global_context);

    // Lançamento das Threads
    std::vector<std::thread> thread_pool;
    thread_pool.emplace_back([task_reconstruction]() { task_reconstruction->run(); });  // [0]
    thread_pool.emplace_back([task_camera]() { task_camera->run(); });                  // [1]
    thread_pool.emplace_back([task_nav_cmd]() { task_nav_cmd->run(); });                // [2]
    thread_pool.emplace_back([task_nav_ctrl]() { task_nav_ctrl->run(); });              // [3]
    thread_pool.emplace_back([task_dist_calc]() { task_dist_calc->run(); });            // [4]
    thread_pool.emplace_back([task_collector]() { task_collector->run(); });            // [5]
    thread_pool.emplace_back([task_mqtt_bridge]() { task_mqtt_bridge->run(); });        // [6]

    // ── RT Linux: mlockall APÓS criar threads (stacks já alocados → sem EAGAIN) ──
    if (mlockall(MCL_CURRENT | MCL_FUTURE) != 0) {
        core::TerminalPrinter::Log(core::TerminalPrinter::Level::Warning, "RT",
                                   "mlockall falhou — rode como root para melhor determinismo.");
    } else {
        core::TerminalPrinter::Log(core::TerminalPrinter::Level::Success, "RT",
                                   "Memória travada (mlockall OK).");
    }

    // ── RT Linux: prioridades Rate-Monotonic (período menor = prioridade maior) ──
    // SCHED_FIFO prio [1,99]: DistanceCalc(20ms)>NavCmd/Ctrl(80ms)>SurfaceRecon(100ms)
    setThreadRT(thread_pool[4], 50);  // DistanceCalculator   — 20ms
    setThreadRT(thread_pool[2], 40);  // NavigationCommand    — 80ms
    setThreadRT(thread_pool[3], 39);  // NavigationControl    — 80ms
    setThreadRT(thread_pool[0], 30);  // SurfaceReconstruction— 100ms
    setThreadRT(thread_pool[5], 20);  // DataCollector        — event
    setThreadRT(thread_pool[1], 15);  // CameraInspection     — event
    setThreadRT(thread_pool[6], 10);  // MqttBridge           — 200ms

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
