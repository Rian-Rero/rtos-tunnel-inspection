/**
 * @file SurfaceReconstruction.cpp
 * @brief Implementação da tarefa de reconstrução da superfície do teto do túnel.
 */
#include "tasks/SurfaceReconstruction.hpp"

#include <chrono>
#include <thread>

#include "core/TerminalPrinter.hpp"

namespace tasks {

/**
 * @brief Construtor da tarefa de Reconstrução de Superfície.
 * * @param buffer Ponteiro compartilhado para a fila thread-safe onde os dados da superfície serão
 * publicados.
 * @param context Ponteiro compartilhado para o contexto global para gerenciamento de estado e
 * acionamento de eventos.
 * @param threshold Valor limite de distância do LIDAR (em metros) para considerar uma variação
 * severa (anomalia).
 */
SurfaceReconstruction::SurfaceReconstruction(
    std::shared_ptr<core::ThreadSafeQueue<core::SurfaceData>> buffer,
    std::shared_ptr<core::SharedContext> context, double threshold)
    : surface_buffer_(buffer), context_(context), threshold_anomaly_(threshold) {}

/**
 * @brief Executa o loop principal da tarefa de reconstrução da superfície do teto do túnel.
 *
 * Emula a leitura dos dados do sensor LIDAR, detecta variações severas e publica os dados
 * empacotados no buffer. Utiliza sincronismo absoluto (sleep_until) para garantir a execução
 * cíclica estrita a cada 100 ms, mitigando os problemas de drift temporal causados pelo tempo de
 * execução das instruções e jitter do SO.
 */
void SurfaceReconstruction::run() {
    double simulated_x = 0.0;

    // Configuração do ponto de sincronismo absoluto para mitigar o clock drift
    auto proximo_ciclo = std::chrono::steady_clock::now();
    const auto periodo = std::chrono::milliseconds(100);

    while (context_->is_running) {
        // Define o momento exato em que o próximo ciclo deve iniciar
        proximo_ciclo += periodo;

        // Emulação de leitura do LIDAR
        double simulated_lidar_y = 2.0;  // altura de um teto normal

        // Simula um buraco na posição X = 5.0
        if (simulated_x > 4.8 && simulated_x < 5.2) {
            simulated_lidar_y = 3.5;
        }

        // Lógica de detecção de anomalia
        if (simulated_lidar_y > threshold_anomaly_ && !context_->isAnomalyActive()) {
            core::TerminalPrinter::Log(core::TerminalPrinter::Level::Warning, "Reconstrucao",
                                       "ALERTA: Variacao severa! Disparando evento.");
            context_->triggerAnomaly();
        }

        // Criação e envio do pacote de dados
        core::SurfaceData data{
            static_cast<uint64_t>(std::chrono::system_clock::now().time_since_epoch().count()),
            simulated_x, simulated_lidar_y,
            0.98  // Nível de confiança emulado da medição
        };

        surface_buffer_->push(data);

        simulated_x += 0.2;  // Avança a posição simulada do robô

        // Suspende a thread até o momento previamente agendado, compensando o tempo gasto na lógica
        // acima
        std::this_thread::sleep_until(proximo_ciclo);
    }
}

}  // namespace tasks