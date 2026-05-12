/**
 * @file NavigationCommand.hpp
 * @brief Declaração da tarefa de geração de comandos de navegação.
 */
#pragma once
#include <memory>

#include "Itask.hpp"
#include "core/DataTypes.hpp"
#include "core/SharedContext.hpp"
#include "core/ThreadSafeQueue.hpp"

namespace tasks {

/**
 * @class NavigationCommand
 * @brief Tarefa que publica setpoints de navegação no buffer IPC.
 *
 * @details Ajusta o setpoint em função do estado de anomalia e publica
 * periodicamente na fila compartilhada.
 */
class NavigationCommand : public ITask {
   private:
    std::shared_ptr<core::SharedContext> context_; /**< Contexto global compartilhado. */
    std::shared_ptr<core::ThreadSafeQueue<core::NavigationSetpoint>>
        cmd_queue_; /**< Buffer de comandos de navegação. */

   public:
    /**
     * @brief Construtor da tarefa NavigationCommand.
     * @param ctx Ponteiro compartilhado para o contexto global.
     * @param queue Ponteiro compartilhado para a fila de setpoints.
     */
    NavigationCommand(std::shared_ptr<core::SharedContext> ctx,
                      std::shared_ptr<core::ThreadSafeQueue<core::NavigationSetpoint>> queue);

    /**
     * @brief Executa o loop principal da tarefa.
     */
    void run() override;
};

}  // namespace tasks