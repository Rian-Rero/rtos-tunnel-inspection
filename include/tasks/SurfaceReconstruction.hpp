/**
 * @file SurfaceReconstruction.hpp
 * @brief Declaração da tarefa de reconstrução da superfície do túnel.
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
 * @brief Tarefa que simula o LIDAR e publica dados da superfície.
 *
 * @details Detecta variações severas (anomalias) e sinaliza o contexto
 * compartilhado para disparar inspeção detalhada.
 */
class SurfaceReconstruction : public ITask {
   private:
    std::shared_ptr<core::ThreadSafeQueue<core::SurfaceData>>
        surface_buffer_;                           /**< Buffer de dados de superfície. */
    std::shared_ptr<core::SharedContext> context_; /**< Contexto global compartilhado. */
    double threshold_anomaly_;                     /**< Limite para detectar anomalia. */

   public:
    /**
     * @brief Construtor da tarefa SurfaceReconstruction.
     * @param buffer Ponteiro compartilhado para o buffer de dados.
     * @param context Ponteiro compartilhado para o contexto global.
     * @param threshold Limite de distância para detectar anomalia.
     */
    SurfaceReconstruction(std::shared_ptr<core::ThreadSafeQueue<core::SurfaceData>> buffer,
                          std::shared_ptr<core::SharedContext> context, double threshold);

    /**
     * @brief Executa o loop principal da tarefa.
     */
    void run() override;
};

}  // namespace tasks