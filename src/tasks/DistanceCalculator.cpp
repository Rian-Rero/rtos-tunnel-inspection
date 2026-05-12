#include "tasks/DistanceCalculator.hpp"
#include <chrono>
#include <iostream>
#include <thread>

namespace tasks {

DistanceCalculator::DistanceCalculator(std::shared_ptr<core::SharedContext> ctx)
    : context_(ctx), total_distance_(0.0), last_encoder_state_(false) {}

void DistanceCalculator::run() {
    int sim_counter = 0;
    
    auto next_wakeup = std::chrono::steady_clock::now();
    const auto cycle_time = std::chrono::milliseconds(20);

    while (context_->is_running) {
        next_wakeup += cycle_time;

        sim_counter++;
        bool current_encoder_state = last_encoder_state_;
        
        // Simulação do sinal do encoder (troca a cada 50 ciclos = 1 segundo)
        if (sim_counter >= 50) {
            current_encoder_state = !last_encoder_state_;
            sim_counter = 0;
        }

        if (current_encoder_state != last_encoder_state_) {
            total_distance_ += 1.0; 
            std::cout << "[ENCODER] Odometria Atualizada: " << total_distance_ << "m\n";
        }
        
        last_encoder_state_ = current_encoder_state;

        std::this_thread::sleep_until(next_wakeup); 
    }
}

double DistanceCalculator::getTotalDistance() const {
    return total_distance_;
}

} // namespace tasks