/**
 * @file SurfaceReconstruction.hpp
 * @brief Declaracao da tarefa de reconstrucao da superficie do tunel.
 */
#pragma once
#include <memory>

#include "core/DataTypes.hpp"
#include "core/SharedContext.hpp"
#include "core/ThreadSafeQueue.hpp"
#include "tasks/Itask.hpp"

namespace tasks {

/**
 * @class SurfaceReconstruction
 * @brief Tarefa que simula o LIDAR e publica dados da superficie.
 *
 * Detecta variacoes severas (anomalias) e sinaliza o contexto
 * compartilhado para disparar inspeccao detalhada.
 */
class SurfaceReconstruction : public ITask {
   private:
    std::shared_ptr<core::ThreadSafeQueue<core::SurfaceData>>
        surface_buffer_;                           /**< Buffer de dados de superficie. */
    std::shared_ptr<core::SharedContext> context_; /**< Contexto global compartilhado. */
    double threshold_anomaly_;                     /**< Limite para detectar anomalia. */

   public:
    /**
     * @brief Construtor da tarefa SurfaceReconstruction.
     * @param buffer Ponteiro compartilhado para o buffer de dados.
     * @param context Ponteiro compartilhado para o contexto global.
     * @param threshold Limite de distancia para detectar anomalia.
     */
    SurfaceReconstruction(std::shared_ptr<core::ThreadSafeQueue<core::SurfaceData>> buffer,
                          std::shared_ptr<core::SharedContext> context, double threshold);

    /**
     * @brief Executa o loop principal da tarefa.
     */
    void run() override;
};

}  // namespace tasks