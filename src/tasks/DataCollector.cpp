/**
 * @file DataCollector.cpp
 * @brief Implementação da tarefa de coleta e persistência de dados.
 * @details Esta classe é responsável por consumir os dados da superfície do túnel
 * a partir de um buffer compartilhado (IPC) e gravar os mesmos em um arquivo CSV.
 * Calcula também dinamicamente o nível de confiabilidade da leitura com base
 * na distância entre os pontos, utilizando um modelo matemático de decaimento exponencial.
 */
#include "tasks/DataCollector.hpp"

#include <algorithm>  // Necessário para std::clamp
#include <cmath>      // Necessário para std::abs e std::exp
#include <cstdlib>
#include <sstream>
#include <string>

#include "core/TerminalPrinter.hpp"

namespace tasks {

namespace {

std::string escapeForShell(const std::string& value) {
    std::string escaped;
    escaped.reserve(value.size() + 8);
    for (char ch : value) {
        if (ch == '\'') {
            escaped += "'\"'\"'";
        } else {
            escaped += ch;
        }
    }
    return escaped;
}

void publishMqtt(const std::string& topic, const std::string& payload) {
    const std::string command = "printf '%s\\n' '" + escapeForShell(payload) +
                                "' | mosquitto_pub -h localhost -t '" + escapeForShell(topic) +
                                "' -l";
    std::system(command.c_str());
}

}  // namespace

/**
 * @brief Construtor da tarefa DataCollector.
 * @param buffer Ponteiro compartilhado para a fila thread-safe que contém os dados da superfície.
 * @param context Ponteiro compartilhado para o contexto global de estado do sistema.
 * @param log_filename Caminho e nome do arquivo CSV onde os registros serão salvos.
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
 * @brief Destrutor da classe DataCollector.
 * @details Garante o encerramento seguro do arquivo de log, descarregando
 * qualquer dado remanescente no buffer da stream para o disco.
 */
DataCollector::~DataCollector() {
    if (log_file_.is_open()) {
        log_file_.close();
    }
}

/**
 * @brief Executa o loop principal da tarefa de coleta e processamento de dados.
 * @details Retira continuamente os pacotes de dados da fila bloqueante.
 * Calcula o espaço percorrido (`delta_x`) para determinar o nível de confiabilidade
 * da medição de forma contínua através de uma função de decaimento exponencial.
 * Após o cálculo, grava o registro final atualizado no arquivo CSV.
 */
void DataCollector::run() {
    double last_x = 0.0;

    while (context_->is_running) {
        core::SurfaceData data;

        // Fica dormindo (bloqueado) na fila até receber dados novos ou a fila ser fechada
        if (!surface_buffer_->pop(data)) {
            break;
        }

        // Dupla verificação de segurança caso o sistema solicite encerramento (shutdown)
        if (!context_->is_running) {
            break;
        }

        // --- INÍCIO DA ANÁLISE CONTÍNUA DE CONFIABILIDADE ---

        // Calcula a distância entre a posição da leitura atual e a anterior
        double delta_x = std::abs(data.position_x - last_x);

        // Fator de decaimento (lambda): calibra a severidade da perda de confiança.
        // Pode ser calibrado de acordo com a resolução nominal do sensor LIDAR real.
        const double lambda = 1.5;

        // Aplica a função de decaimento exponencial: e^(-lambda * delta_x)
        double calculated_confidence = std::exp(-lambda * delta_x);

        // Limita a confiança de forma segura para não ultrapassar 100% (1.0)
        // ou cair para valores irrealistas (mínimo de 10% ou 0.1)
        calculated_confidence = std::clamp(calculated_confidence, 0.1, 1.0);

        // Substitui a confiabilidade emulada pela confiabilidade física calculada
        data.confidence_level = calculated_confidence;
        last_x = data.position_x;

        // --- FIM DA ANÁLISE ---

        // Persistência em disco: grava os dados processados e força o fluxo (flush)
        if (log_file_.is_open()) {
            log_file_ << data.timestamp << "," << data.position_x << "," << data.lidar_distance_y
                      << "," << data.confidence_level << "\n";
            log_file_.flush();
        }

        std::ostringstream telemetry;
        telemetry << "{"
                  << "\"timestamp\":" << data.timestamp << ","
                  << "\"position_x\":" << data.position_x << ","
                  << "\"pos_x\":" << data.position_x << ","
                  << "\"distance_m\":" << (data.position_x / 10.0) << ","
                  << "\"lidar_distance_y\":" << data.lidar_distance_y << ","
                  << "\"lidar\":" << data.lidar_distance_y << ","
                  << "\"imu\":" << 0.0 << ","
                  << "\"confidence_level\":" << data.confidence_level << ","
                  << "\"current_speed\":" << context_->current_speed.load() << ","
                  << "\"velocidade\":" << context_->current_speed.load() << ","
                  << "\"manual_mode\":" << (context_->manual_mode.load() ? "true" : "false") << ","
                  << "\"mode\":\"" << (context_->manual_mode.load() ? "MANUAL" : "AUTO") << "\","
                  << "\"speed_setpoint\":" << context_->speed_setpoint.load() << ","
                  << "\"direction\":" << context_->direction.load() << ","
                  << "\"direction_label\":\""
                  << (context_->direction.load() < 0   ? "LEFT"
                      : context_->direction.load() > 0 ? "RIGHT"
                                                       : "STOP")
                  << "\"}";

        publishMqtt("telemetry/robot", telemetry.str());
        publishMqtt("sensor/lidar", std::to_string(data.lidar_distance_y));
        publishMqtt("sensor/encoder", std::to_string(static_cast<int>(data.position_x > 0.0)));

        // Impressão no terminal para monitoramento e depuração (Debug)
        core::TerminalPrinter::Log(core::TerminalPrinter::Level::Info, "Coletor",
                                   "Log salvo - X: " + std::to_string(data.position_x) +
                                       "m | Y: " + std::to_string(data.lidar_distance_y) +
                                       "m | Conf: " + std::to_string(data.confidence_level));
    }
}

}  // namespace tasks