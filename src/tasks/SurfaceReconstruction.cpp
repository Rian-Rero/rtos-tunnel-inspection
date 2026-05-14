/**
 * @file SurfaceReconstruction.cpp
 * @brief Implementação da tarefa de reconstrução da superfície do teto do túnel.
 */
#include "tasks/SurfaceReconstruction.hpp"

#include <chrono>
#include <cmath>
#include <random>
#include <thread>

#include "core/TerminalPrinter.hpp"

namespace tasks {

/**
 * @brief Construtor da tarefa de reconstrução de superfície.
 * @param buffer Ponteiro compartilhado para a fila thread-safe onde os dados da superfície serão
 * publicados.
 * @param context Ponteiro compartilhado para o contexto global para gerenciamento de estado e
 * acionamento de eventos.
 * @param threshold Valor limite de variação de distância do LIDAR (em metros) para considerar uma
 * anomalia severa.
 */
SurfaceReconstruction::SurfaceReconstruction(
    std::shared_ptr<core::ThreadSafeQueue<core::SurfaceData>> buffer,
    std::shared_ptr<core::SharedContext> context, double threshold)
    : surface_buffer_(buffer), context_(context), threshold_anomaly_(threshold) {}

/**
 * @brief Executa o loop principal da tarefa de reconstrução da superfície do teto do túnel.
 *
 * @details Emula a leitura dos dados do sensor LIDAR em um túnel infinito.
 * Detecta variações severas (buracos ou saliências) e publica os dados empacotados no buffer.
 * Utiliza sincronismo absoluto (sleep_until) para garantir a execução cíclica estrita a cada 100
 * ms.
 */
void SurfaceReconstruction::run() {
    double simulated_x = 0.0;

    // Configuração do ponto de sincronismo absoluto para mitigar o clock drift
    auto proximo_ciclo = std::chrono::steady_clock::now();
    const auto periodo = std::chrono::milliseconds(100);

    // Gerador de números aleatórios para criar o túnel infinito dinamicamente
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_real_distribution<> prob_dist(0.0, 1.0);
    std::uniform_real_distribution<> size_dist(0.5, 2.0);  // Tamanho da anomalia (metros)

    bool inside_anomaly = false;
    double anomaly_end_x = 0.0;
    double current_anomaly_y = 2.0;

    while (context_->is_running) {
        // Define o momento exato em que o próximo ciclo deve iniciar
        proximo_ciclo += periodo;

        // Emulação de leitura do LIDAR
        double simulated_lidar_y = 2.0;  // Altura normal de um teto plano

        // Lógica: 3% de chance a cada ciclo (100ms) de começar uma nova anomalia
        if (!inside_anomaly && prob_dist(gen) < 0.03) {
            inside_anomaly = true;
            anomaly_end_x = simulated_x + size_dist(gen);

            // 50% de chance de ser um buraco, 50% de chance de ser uma saliência
            if (prob_dist(gen) > 0.5) {
                current_anomaly_y = 2.0 + (prob_dist(gen) * 2.0);  // Buraco (2.0m até 4.0m)
            } else {
                current_anomaly_y = 2.0 - (prob_dist(gen) * 1.0);  // Saliência (1.0m até 2.0m)
            }
        }

        if (inside_anomaly) {
            if (simulated_x < anomaly_end_x) {
                simulated_lidar_y = current_anomaly_y;
            } else {
                // Passou da anomalia, o teto volta ao normal
                inside_anomaly = false;
                simulated_lidar_y = 2.0;
            }
        }

        // Análise contínua: Uma variação maior que o limite configurado gera o alerta
        // Utilizamos o valor absoluto para pegar tanto buracos quanto saliências
        double variacao = std::abs(simulated_lidar_y - 2.0);
        double limite_variacao = std::abs(threshold_anomaly_ - 2.0);

        if (variacao >= limite_variacao) {
            if (!context_->isAnomalyActive()) {
                core::TerminalPrinter::Log(core::TerminalPrinter::Level::Warning, "Reconstrução",
                                           "ALERTA: Variação estrutural (" +
                                               std::to_string(simulated_lidar_y) +
                                               "m)! Disparando evento.");
                context_->triggerAnomaly();
            }
        } else {
            if (context_->isAnomalyActive()) {
                core::TerminalPrinter::Log(core::TerminalPrinter::Level::Info, "Reconstrução",
                                           "Superfície normalizada. Robô retomando cruzeiro.");
                context_->resetAnomaly();  // Rearma o sistema para a próxima anomalia
            }
        }

        // Criação e envio do pacote de dados
        core::SurfaceData data{
            static_cast<uint64_t>(std::chrono::system_clock::now().time_since_epoch().count()),
            simulated_x, simulated_lidar_y,
            0.98  // Nível de confiança emulado
        };

        if (!surface_buffer_->push(data)) {
            break;
        }

        /**
         * @brief Cálculo do deslocamento físico real.
         * Lê a velocidade atual da malha de controle, converte de porcentagem 
         * para metros por segundo (assumindo 100% = 2.0 m/s), e calcula a distância 
         * percorrida no tempo de amostragem deste ciclo (100ms = 0.1s).
         */
        double speed_percent = context_->current_speed.load();
        double speed_ms = (speed_percent / 100.0) * 2.0;
        double delta_x = speed_ms * 0.1;
        
        // Impede recuo negativo na simulação do sensor caso o freio seja brusco
        if (delta_x < 0.0) {
            delta_x = 0.0; 
        }

        simulated_x += delta_x; // Avança a posição baseada na física real

        // Suspende a thread até o momento previamente agendado
        std::this_thread::sleep_until(proximo_ciclo);
    }
}

}  // namespace tasks