/**
 * @file NavigationControl.cpp
 * @brief Implementação da tarefa de controle de navegação.
 */
#include "tasks/NavigationControl.hpp"

#include <algorithm>
#include <chrono>
#include <iomanip>
#include <sstream>
#include <thread>

#include "core/TerminalPrinter.hpp"

namespace tasks {

/**
 * @brief Construtor da tarefa NavigationControl.
 * @param ctx Ponteiro compartilhado para o contexto global.
 * @param queue Ponteiro compartilhado para a fila de setpoints.
 */
NavigationControl::NavigationControl(
    std::shared_ptr<core::SharedContext> ctx,
    std::shared_ptr<core::ThreadSafeQueue<core::NavigationSetpoint>> queue)
    : context_(ctx),
      cmd_queue_(queue),
      Kp_(1.5),
      Ki_(0.8),
      Kd_(0.1),
      integral_error_(0.0),
      previous_error_(0.0) {}

/**
 * @brief Calcula o sinal de controle PID.
 * @param setpoint Setpoint de velocidade.
 * @param current_speed Velocidade atual simulada.
 * @param dt Tempo de amostragem.
 * @return Saída do controlador limitada.
 */
int NavigationControl::computePID(int setpoint, int current_speed, double dt) {
    double error = setpoint - current_speed;

    integral_error_ += error * dt;
    integral_error_ = std::clamp(integral_error_, -50.0, 50.0);  // Anti-windup

    double derivative = (error - previous_error_) / dt;
    previous_error_ = error;

    double output = (Kp_ * error) + (Ki_ * integral_error_) + (Kd_ * derivative);

    return static_cast<int>(std::clamp(output, -100.0, 100.0));
}

/**
 * @brief Executa o loop principal da tarefa de controle.
 * @details Consome os setpoints do buffer IPC, calcula o esforço de controle (PID)
 * e simula a inércia do robô. A velocidade de saída simulada (PV) é então publicada 
 * no contexto global para ser consumida pela física dos sensores em outras threads.
 */
void NavigationControl::run() {
    double current_simulated_speed = 0;

    auto next_wakeup = std::chrono::steady_clock::now();
    const auto cycle_time = std::chrono::milliseconds(80);
    const double Ts = 0.08;  // Tempo de amostragem fixo e garantido pelo RTOS (80ms)

    while (context_->is_running) {
        next_wakeup += cycle_time;

        core::NavigationSetpoint sp;
        // Consome a mensagem via IPC de forma segura
        if (!cmd_queue_->tryPop(sp)) {
            if (cmd_queue_->isClosed()) {
                break;
            }
            sp.speed_setpoint = 0;
        }

        int o_aceleracao = computePID(sp.speed_setpoint, current_simulated_speed, Ts);

        // Simulação básica da planta
        current_simulated_speed += (o_aceleracao - current_simulated_speed) * 0.15;

        // Publica a velocidade na variável atômica global
        context_->current_speed.store(current_simulated_speed);

        std::ostringstream oss;
        oss << std::fixed << std::setprecision(1);
        oss << "SP: " << sp.speed_setpoint << "% | PV: " << current_simulated_speed
            << "% | OUT: " << o_aceleracao << "%";
        core::TerminalPrinter::Log(core::TerminalPrinter::Level::Debug, "CTRL", oss.str());

        // Dorme até o instante exato do próximo ciclo
        std::this_thread::sleep_until(next_wakeup);
    }
}

}  // namespace tasks