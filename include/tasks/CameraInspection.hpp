/**
 * @file CameraInspection.hpp
 * @brief Declaração da tarefa de inspeção detalhada com câmera.
 */
#pragma once
#include <memory>

#include "core/SharedContext.hpp"
#include "tasks/Itask.hpp"

namespace tasks {

/**
 * @class CameraInspection
 * @brief Tarefa que realiza inspeção detalhada quando uma anomalia é detectada.
 *
 * @details A tarefa aguarda o sinal do contexto compartilhado e executa uma rotina
 * de processamento pesado, simulando a análise com câmera/IA.
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