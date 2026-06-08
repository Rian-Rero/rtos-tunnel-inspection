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
#include <sstream>
#include <string>

#include "core/MqttPublisher.hpp"
#include "core/TaskTimingLogger.hpp"
#include "core/TerminalPrinter.hpp"

namespace tasks {

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
    uint64_t invocation_num = 0;
    core::MqttPublisher telemetry_pub("telemetry/robot");
    core::MqttPublisher lidar_pub("sensor/lidar");
    core::MqttPublisher imu_pub("sensor/imu");
    core::MqttPublisher encoder_pub("sensor/encoder");

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

        auto actual = std::chrono::steady_clock::now();

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
        const double imu_degrees = context_->imu_degrees.load();
        const int encoder_count = static_cast<int>(std::llround(data.position_x * 100.0));
        const bool manual_mode = context_->manual_mode.load();
        const int manual_speed_setpoint = context_->speed_setpoint.load();
        const double current_speed = context_->current_speed.load();
        const int command_direction = context_->direction.load();
        const int display_direction =
            manual_mode ? command_direction
                        : (current_speed < -0.5 ? -1 : (current_speed > 0.5 ? 1 : 0));
        const int effective_speed_setpoint = manual_mode ? display_direction * manual_speed_setpoint
                                                         : (context_->isAnomalyActive() ? 15 : 50);

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
                  << "\"distance_m\":" << data.position_x << ","
                  << "\"lidar_distance_y\":" << data.lidar_distance_y << ","
                  << "\"lidar\":" << data.lidar_distance_y << ","
                  << "\"imu\":" << imu_degrees << ","
                  << "\"confidence_level\":" << data.confidence_level << ","
                  << "\"current_speed\":" << current_speed << ","
                  << "\"velocidade\":" << current_speed << ","
                  << "\"manual_mode\":" << (manual_mode ? "true" : "false") << ","
                  << "\"mode\":\"" << (manual_mode ? "MANUAL" : "AUTO") << "\","
                  << "\"encoder\":" << encoder_count << ","
                  << "\"speed_setpoint\":" << effective_speed_setpoint << ","
                  << "\"manual_speed_setpoint\":" << manual_speed_setpoint << ","
                  << "\"direction\":" << display_direction << ","
                  << "\"command_direction\":" << command_direction << ","
                  << "\"direction_label\":\""
                  << (display_direction < 0   ? "LEFT"
                      : display_direction > 0 ? "RIGHT"
                                              : "STOP")
                  << "\"}";

        telemetry_pub.publish(telemetry.str());
        lidar_pub.publish(std::to_string(data.lidar_distance_y));
        imu_pub.publish(std::to_string(imu_degrees));
        encoder_pub.publish(std::to_string(encoder_count));

        core::TaskTimingLogger::instance().log(
            {"DataIMU", 0, invocation_num++, core::TaskTimingLogger::toNs(actual),
             core::TaskTimingLogger::toNs(actual),
             core::TaskTimingLogger::toNs(std::chrono::steady_clock::now())});

        // Impressão no terminal para monitoramento e depuração (Debug)
        core::TerminalPrinter::Log(core::TerminalPrinter::Level::Info, "Coletor",
                                   "Log salvo - X: " + std::to_string(data.position_x) +
                                       "m | Y: " + std::to_string(data.lidar_distance_y) +
                                       "m | Conf: " + std::to_string(data.confidence_level));
    }
}

}  // namespace tasks
