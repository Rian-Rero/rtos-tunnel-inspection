#pragma once
#include "Itask.hpp"
#include "core/SharedContext.hpp"
#include "core/ThreadSafeQueue.hpp"
#include "core/DataTypes.hpp"
#include <memory>

namespace tasks {

class NavigationCommand : public ITask {
private:
    std::shared_ptr<core::SharedContext> context_;
    std::shared_ptr<core::ThreadSafeQueue<core::NavigationSetpoint>> cmd_queue_;

public:
    NavigationCommand(std::shared_ptr<core::SharedContext> ctx, 
                      std::shared_ptr<core::ThreadSafeQueue<core::NavigationSetpoint>> queue);
    
    void run() override;
};

} // namespace tasks