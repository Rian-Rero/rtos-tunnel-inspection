/**
 * @file DistanceCalculator.hpp
 * @brief Declaração da tarefa de cálculo de distância.
 */
#pragma once
#include <memory>

#include "Itask.hpp"
#include "core/SharedContext.hpp"

namespace tasks {

/**
 * @class DistanceCalculator
 * @brief Tarefa que estima a distância percorrida via encoder simulado.
 *
 * @details Atualiza o acumulado de distância sempre que detecta transição
 * do sinal do encoder.
 */
class DistanceCalculator : public ITask {
   private:
    std::shared_ptr<core::SharedContext> context_; /**< Contexto global compartilhado. */
    double total_distance_;                        /**< Distância total acumulada em metros. */
    bool last_encoder_state_;                      /**< Último estado do encoder simulado. */

   public:
    /**
     * @brief Construtor da tarefa DistanceCalculator.
     * @param ctx Ponteiro compartilhado para o contexto global.
     */
    DistanceCalculator(std::shared_ptr<core::SharedContext> ctx);

    /**
     * @brief Executa o loop principal da tarefa.
     */
    void run() override;

    /**
     * @brief Retorna a distância total acumulada.
     * @return Distância total em metros.
     */
    double getTotalDistance() const;
};

}  // namespace tasks