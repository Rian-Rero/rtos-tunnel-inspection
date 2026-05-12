/**
 * @file main.cpp
 * @brief Ponto de entrada do sistema de inspeção ATR - Frente de Navegação.
 */
#include <csignal>
#include <iostream>
#include <memory>
#include <string>
#include <thread>
#include <vector>

#include "core/DataTypes.hpp"
#include "core/SharedContext.hpp"
#include "core/ThreadSafeQueue.hpp"
#include "tasks/DistanceCalculator.hpp"
#include "tasks/NavigationCommand.hpp"
#include "tasks/NavigationControl.hpp"

// Ponteiro global para o contexto compartilhado
std::shared_ptr<core::SharedContext> global_context = std::make_shared<core::SharedContext>();

/**
 * @brief Handler para encerramento seguro via sinal do sistema (Ctrl+C).
 */
void signalHandler(int signum) {
    std::cout << "\n[SISTEMA] Sinal (" << signum << ") recebido. Encerrando threads...\n";
    global_context->is_running = false;
    
    // Acorda threads que possam estar bloqueadas em variáveis de condição
    global_context->triggerAnomaly(); 
}

int main() {
    // Configura o tratamento de sinal para encerramento gracioso
    std::signal(SIGINT, signalHandler);

    std::cout << "========================================================\n";
    std::cout << "   SISTEMA DE INSPEÇÃO ATR - MÓDULO DE NAVEGAÇÃO\n";
    std::cout << "========================================================\n";

    // 1. Instanciação dos Buffers IPC
    // Buffer para comandos de velocidade entre NavigationCommand e NavigationControl
    auto command_buffer = std::make_shared<core::ThreadSafeQueue<core::NavigationSetpoint>>(50);

    // 2. Instanciação das Tarefas da Pessoa 1
    auto task_nav_cmd = std::make_shared<tasks::NavigationCommand>(global_context, command_buffer);
    auto task_nav_ctrl = std::make_shared<tasks::NavigationControl>(global_context, command_buffer);
    auto task_dist_calc = std::make_shared<tasks::DistanceCalculator>(global_context);

    // 3. Lançamento das Threads
    std::vector<std::thread> thread_pool;

    std::cout << "[MAIN] Iniciando thread: NavigationCommand (80ms)\n";
    thread_pool.emplace_back([task_nav_cmd]() { task_nav_cmd->run(); });

    std::cout << "[MAIN] Iniciando thread: NavigationControl (80ms)\n";
    thread_pool.emplace_back([task_nav_ctrl]() { task_nav_ctrl->run(); });

    std::cout << "[MAIN] Iniciando thread: DistanceCalculator (20ms)\n";
    thread_pool.emplace_back([task_dist_calc]() { task_dist_calc->run(); });

    std::cout << "[MAIN] Sistema em execução. Pressione Ctrl+C para parar.\n\n";

    // 4. Aguardar encerramento de todas as threads (Join)
    for (auto& t : thread_pool) {
        if (t.joinable()) {
            t.join();
        }
    }

    std::cout << "========================================================\n";
    std::cout << "        SISTEMA DE NAVEGAÇÃO ENCERRADO COM SUCESSO\n";
    std::cout << "========================================================\n";

    return 0;
}