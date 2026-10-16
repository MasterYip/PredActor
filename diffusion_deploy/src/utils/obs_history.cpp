#include "diffusion_deploy/utils/obs_history.hpp"
#include <stdexcept>
#include <sstream>

namespace diffusion_deploy {

ObsHistory::ObsHistory(int n_obs_steps) : n_obs_steps_(n_obs_steps) {}

void ObsHistory::init(const ObsTensorMap& terms) {
    history_.clear();
    for (const auto& [key, value] : terms) {
        // value must have T=1 (shape [B, 1, ...])
        if (value.dim() < 2) {
            throw std::runtime_error(
                "ObsHistory::init: tensor '" + key +
                "' has fewer than 2 dims (expected [B, T, ...])");
        }
        if (value.size(1) != 1) {
            std::ostringstream oss;
            oss << "ObsHistory::init: tensor '" << key
                << "' has T=" << value.size(1) << " (expected T=1)";
            throw std::runtime_error(oss.str());
        }
        // Repeat along time dimension: [B, 1, ...] -> [B, n_obs_steps, ...]
        std::vector<int64_t> repeat_shape(value.dim(), 1);
        repeat_shape[1] = n_obs_steps_;
        history_[key] = value.repeat(repeat_shape);
    }
    initialized_ = true;
}

void ObsHistory::shift_append(const ObsTensorMap& latest) {
    if (!initialized_) {
        throw std::runtime_error("ObsHistory::shift_append called before init()");
    }
    for (auto& [key, hist] : history_) {
        auto it = latest.find(key);
        if (it == latest.end()) {
            throw std::runtime_error(
                "ObsHistory::shift_append: key '" + key + "' missing in latest terms");
        }
        const auto& new_val = it->second;
        // hist: [B, T, ...]   new_val: [B, 1, ...]
        // result: cat([hist[:, 1:], new_val], dim=1)
        history_[key] = torch::cat({hist.slice(1, 1), new_val}, /*dim=*/1);
    }
}

}  // namespace diffusion_deploy
