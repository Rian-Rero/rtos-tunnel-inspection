/**
 * @file CameraInspection.hpp
 * @brief Declaracao da tarefa de inspecao detalhada com camera.
 */
#pragma once
#include <memory>

#include "core/SharedContext.hpp"
#include "tasks/Itask.hpp"

namespace tasks {

/**
 * @class CameraInspection
 * @brief Tarefa que realiza inspecao detalhada quando uma anomalia e detectada.
 *
 * A tarefa aguarda o sinal do contexto compartilhado e executa uma rotina
 * de processamento pesado, simulando a analise com camera/IA.
 */
class CameraInspection : public ITask {
   private:
    std::shared_ptr<core::SharedContext> context_; /**< Contexto global compartilhado. */

   public:
    /**
     * @brief Construtor da tarefa CameraInspection.
     * @param context Ponteiro compartilhado para o contexto global.
     */
    explicit CameraInspection(std::shared_ptr<core::SharedContext> context);

    /**
     * @brief Executa o loop principal da tarefa.
     */
    void run() override;
};

}  // namespace tasks