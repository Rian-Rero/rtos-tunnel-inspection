/**
 * @file SharedContext.cpp
 * @brief Implementação do contexto compartilhado do sistema.
 */
#include "core/SharedContext.hpp"

namespace core {

void SharedContext::triggerAnomaly() {
    std::lock_guard<std::mutex> lock(anomaly_mutex_);
    anomaly_detected_ = true;
    anomaly_cv_.notify_all();
}

void SharedContext::resetAnomaly() {
    std::lock_guard<std::mutex> lock(anomaly_mutex_);
    anomaly_detected_ = false;
}

void SharedContext::waitForAnomaly() {
    std::unique_lock<std::mutex> lock(anomaly_mutex_);
    anomaly_cv_.wait(lock, [this]() { return anomaly_detected_ || !is_running; });
}

bool SharedContext::isAnomalyActive() {
    std::lock_guard<std::mutex> lock(anomaly_mutex_);
    return anomaly_detected_;
}

}  // namespace core