/**
 * @file NavigationControl.hpp
 * @brief Declaração da tarefa de controle de navegação.
 */
#pragma once
#include <memory>

#include "Itask.hpp"
#include "core/DataTypes.hpp"
#include "core/SharedContext.hpp"
#include "core/ThreadSafeQueue.hpp"

namespace tasks {

/**
 * @class NavigationControl
 * @brief Tarefa que aplica controle PID sobre o setpoint de navegação.
 *
 * @details Consome setpoints da fila e simula a resposta da planta,
 * gerando o sinal de controle com anti-windup.
 */
class NavigationControl : public ITask {
   private:
    std::shared_ptr<core::SharedContext> context_; /**< Contexto global compartilhado. */
    std::shared_ptr<core::ThreadSafeQueue<core::NavigationSetpoint>>
        cmd_queue_; /**< Buffer de comandos de navegação. */

    // Ganhos do controlador
    double Kp_, Ki_, Kd_;

    // Memória do controlador discreto
    double integral_error_;
    double previous_error_;

    /**
     * @brief Calcula o sinal de controle PID.
     * @param setpoint Setpoint de velocidade.
     * @param current_speed Velocidade atual simulada.
     * @param dt Tempo de amostragem.
     * @return Saída do controlador limitada.
     */
    int computePID(int setpoint, int current_speed, double dt);

   public:
    /**
     * @brief Construtor da tarefa NavigationControl.
     * @param ctx Ponteiro compartilhado para o contexto global.
     * @param queue Ponteiro compartilhado para a fila de setpoints.
     */
    NavigationControl(std::shared_ptr<core::SharedContext> ctx,
                      std::shared_ptr<core::ThreadSafeQueue<core::NavigationSetpoint>> queue);

    /**
     * @brief Executa o loop principal da tarefa.
     */
    void run() override;
};

}  // namespace tasks