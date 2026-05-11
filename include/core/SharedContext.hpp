/**
 * @file SharedContext.hpp
 * @brief Contexto compartilhado para controle de estado global do robô.
 */
#pragma once
#include <atomic>
#include <condition_variable>
#include <mutex>

namespace core {

/**
 * @class SharedContext
 * @brief Gerencia os estados globais e eventos de anomalia do sistema.
 * * Utiliza variáveis atômicas para estados simples e condition variables para
 * acordar threads que aguardam eventos (como a ativação da Câmera IA).
 */
class SharedContext {
   private:
    std::mutex anomaly_mutex_;
    std::condition_variable anomaly_cv_;
    bool anomaly_detected_{false};

   public:
    std::atomic<bool> is_running{true}; /**< Flag global para encerramento gracioso das threads */

    /**
     * @brief Sinaliza a detecção de uma anomalia estrutural (buraco/saliência).
     * Acorda todas as threads que estão aguardando esse evento.
     */
    void triggerAnomaly() {
        std::lock_guard<std::mutex> lock(anomaly_mutex_);
        anomaly_detected_ = true;
        anomaly_cv_.notify_all();
    }

    /**
     * @brief Redefine o estado de anomalia para falso após a inspeção ser concluída.
     */
    void resetAnomaly() {
        std::lock_guard<std::mutex> lock(anomaly_mutex_);
        anomaly_detected_ = false;
    }

    /**
     * @brief Suspende a thread atual até que uma anomalia seja detectada.
     */
    void waitForAnomaly() {
        std::unique_lock<std::mutex> lock(anomaly_mutex_);
        anomaly_cv_.wait(lock, [this]() { return anomaly_detected_; });
    }

    /**
     * @brief Verifica ativamente se há uma anomalia ocorrendo neste momento.
     * @return true se houver anomalia, false caso contrário.
     */
    bool isAnomalyActive() {
        std::lock_guard<std::mutex> lock(anomaly_mutex_);
        return anomaly_detected_;
    }
};

}  // namespace core