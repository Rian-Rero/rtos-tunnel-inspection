#pragma once
#include "Itask.hpp"
#include "core/SharedContext.hpp"
#include <memory>

namespace tasks {

class DistanceCalculator : public ITask {
private:
    std::shared_ptr<core::SharedContext> context_;
    double total_distance_;
    bool last_encoder_state_;

public:
    DistanceCalculator(std::shared_ptr<core::SharedContext> ctx);
    
    void run() override;
    double getTotalDistance() const;
};

} // namespace tasks