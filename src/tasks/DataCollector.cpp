/**
 * @file DataCollector.cpp
 * @brief Implementação da tarefa de coleta e persistência de dados.
 */
#include "tasks/DataCollector.hpp"

#include <cmath>  // Necessário para usar std::abs no cálculo da confiança
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
 * @details Retira os dados da fila, calcula a variação da posição (delta_x)
 * para determinar o nível de confiança online, e grava o registo atualizado no ficheiro CSV.
 */
void DataCollector::run() {
    double last_x = 0.0;

    while (context_->is_running) {
        // Dorme na fila até ter dados ou até a fila ser fechada
        core::SurfaceData data;
        if (!surface_buffer_->pop(data)) {
            break;
        }

        if (!context_->is_running)
            break;

        // --- INÍCIO DA ANÁLISE ONLINE DE CONFIANÇA ---
        // Calcula a distância entre a leitura atual e a anterior
        double delta_x = std::abs(data.position_x - last_x);

        double calculated_confidence = 0.0;

        if (delta_x <= 0.05) {
            calculated_confidence = 0.99;  // Alta densidade (robô lento), altíssima confiança
        } else if (delta_x <= 0.2) {
            calculated_confidence = 0.90;  // Velocidade de cruzeiro normal
        } else if (delta_x <= 0.5) {
            calculated_confidence = 0.75;  // Leitura rápida, confiança média
        } else {
            calculated_confidence = 0.50;  // Leitura muito espaçada, baixa confiança
        }

        // Substitui o valor emulado pelo valor real calculado online no coletor
        data.confidence_level = calculated_confidence;
        last_x = data.position_x;
        // --- FIM DA ANÁLISE ---

        if (log_file_.is_open()) {
            log_file_ << data.timestamp << "," << data.position_x << "," << data.lidar_distance_y
                      << "," << data.confidence_level << "\n";
            log_file_.flush();
        }

        // Para visualização no console
        core::TerminalPrinter::Log(core::TerminalPrinter::Level::Info, "Coletor",
                                   "Log salvo - X: " + std::to_string(data.position_x) +
                                       "m | Y: " + std::to_string(data.lidar_distance_y) +
                                       "m | Conf: " + std::to_string(data.confidence_level));
    }
}

}  // namespace tasks