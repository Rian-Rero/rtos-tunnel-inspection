/**
 * @file DataCollector.cpp
 * @brief Implementação da tarefa de coleta e persistência de dados.
 */
#include "tasks/DataCollector.hpp"

#include <string>

#include "core/TerminalPrinter.hpp"

namespace tasks {

/**
 * @brief Construtor da tarefa DataCollector.
 * @param buffer Ponteiro compartilhado para o buffer de dados.
 * @param context Ponteiro compartilhado para o contexto global.
 * @param log_filename Caminho e nome do ficheiro onde os dados serão salvos.
 */
DataCollector::DataCollector(std::shared_ptr<core::ThreadSafeQueue<core::SurfaceData>> buffer,
                             std::shared_ptr<core::SharedContext> context,
                             const std::string& log_filename)
    : surface_buffer_(buffer), context_(context) {
    log_file_.open(log_filename);
    if (log_file_.is_open()) {
        log_file_ << "timestamp,x,y,confianca\n";
    }
}

/**
 * @brief Destrutor. Fecha o arquivo de log, se aberto.
 */
DataCollector::~DataCollector() {
    if (log_file_.is_open())
        log_file_.close();
}

/**
 * @brief Executa o loop principal da tarefa.
 */
void DataCollector::run() {
    while (context_->is_running) {
        // Dorme na fila até ter dados ou até a fila ser fechada
        core::SurfaceData data;
        if (!surface_buffer_->pop(data)) {
            break;
        }

        if (!context_->is_running)
            break;

        if (log_file_.is_open()) {
            log_file_ << data.timestamp << "," << data.position_x << "," << data.lidar_distance_y
                      << "," << data.confidence_level << "\n";
            log_file_.flush();
        }

        // Para visualização no console
        core::TerminalPrinter::Log(core::TerminalPrinter::Level::Info, "Coletor",
                                   "Log salvo - X: " + std::to_string(data.position_x) +
                                       "m | Altura (Y): " + std::to_string(data.lidar_distance_y) +
                                       "m");
    }
}
}  // namespace tasks