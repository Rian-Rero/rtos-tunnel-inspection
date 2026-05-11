/**
 * @file DataCollector.hpp
 * @brief Declaracao da tarefa de coleta e persistencia de dados.
 */
#pragma once
#include <fstream>
#include <memory>

#include "core/DataTypes.hpp"
#include "core/SharedContext.hpp"
#include "core/ThreadSafeQueue.hpp"
#include "tasks/Itask.hpp"

namespace tasks {

/**
 * @class DataCollector
 * @brief Tarefa responsavel por persistir os dados de superficie em arquivo.
 *
 * Consome dados do buffer thread-safe, grava em CSV e emite logs
 * para acompanhamento da etapa de testes.
 */
class DataCollector : public ITask {
   private:
    std::shared_ptr<core::ThreadSafeQueue<core::SurfaceData>>
        surface_buffer_;                           /**< Buffer de dados de superficie. */
    std::shared_ptr<core::SharedContext> context_; /**< Contexto global compartilhado. */
    std::ofstream log_file_;                       /**< Arquivo CSV de log. */

   public:
    /**
     * @brief Construtor da tarefa DataCollector.
     * @param buffer Ponteiro compartilhado para o buffer de dados.
     * @param context Ponteiro compartilhado para o contexto global.
     */
    DataCollector(std::shared_ptr<core::ThreadSafeQueue<core::SurfaceData>> buffer,
                  std::shared_ptr<core::SharedContext> context);

    /**
     * @brief Destrutor. Fecha o arquivo de log, se aberto.
     */
    ~DataCollector();

    /**
     * @brief Executa o loop principal da tarefa.
     */
    void run() override;
};
}  // namespace tasks