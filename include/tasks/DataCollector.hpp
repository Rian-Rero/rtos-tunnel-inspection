/**
 * @file DataCollector.hpp
 * @brief Declaração da tarefa de coleta e persistência de dados.
 */
#pragma once

#include <fstream>
#include <memory>
#include <string>

#include "core/DataTypes.hpp"
#include "core/SharedContext.hpp"
#include "core/ThreadSafeQueue.hpp"
#include "tasks/Itask.hpp"

namespace tasks {

/**
 * @class DataCollector
 * @brief Classe responsável por consumir os dados da superfície e gravá-los em um ficheiro CSV.
 */
class DataCollector : public ITask {
   private:
    std::shared_ptr<core::ThreadSafeQueue<core::SurfaceData>> surface_buffer_;
    std::shared_ptr<core::SharedContext> context_;
    std::ofstream log_file_;

   public:
    /**
     * @brief Construtor da tarefa DataCollector com injeção de dependência do nome do ficheiro.
     * @param buffer Ponteiro compartilhado para o buffer de dados.
     * @param context Ponteiro compartilhado para o contexto global.
     * @param log_filename Nome do ficheiro de log (ex: "inspection_log.csv").
     */
    DataCollector(std::shared_ptr<core::ThreadSafeQueue<core::SurfaceData>> buffer,
                  std::shared_ptr<core::SharedContext> context, const std::string& log_filename);

    /**
     * @brief Destrutor. Fecha o ficheiro de log de forma segura.
     */
    ~DataCollector() override;

    /**
     * @brief Executa o loop principal da tarefa de gravação.
     */
    void run() override;
};

}  // namespace tasks