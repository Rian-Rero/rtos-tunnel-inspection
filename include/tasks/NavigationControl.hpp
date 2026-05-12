#pragma once
#include "Itask.hpp"
#include "core/SharedContext.hpp"
#include "core/ThreadSafeQueue.hpp"
#include "core/DataTypes.hpp"
#include <memory>

namespace tasks {

class NavigationControl : public ITask {
private:
    std::shared_ptr<core::SharedContext> context_;
    std::shared_ptr<core::ThreadSafeQueue<core::NavigationSetpoint>> cmd_queue_;
    
    // Ganhos do controlador
    double Kp_, Ki_, Kd_;
    
    // Memória do controlador discreto
    double integral_error_;
    double previous_error_;

    int computePID(int setpoint, int current_speed, double dt);

public:
    NavigationControl(std::shared_ptr<core::SharedContext> ctx, 
                      std::shared_ptr<core::ThreadSafeQueue<core::NavigationSetpoint>> queue);
    
    void run() override;
};

} // namespace tasks