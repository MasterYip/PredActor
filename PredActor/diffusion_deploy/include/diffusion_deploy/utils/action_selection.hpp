#pragma once

#include <cmath>
#include <stdexcept>
#include <string>
#include <vector>

namespace diffusion_deploy {

struct ActionSelection {
    int lower_index;
    int upper_index;
    double alpha;
    int lower_noise_level;
    int upper_noise_level;
};

inline ActionSelection action_selection(
    int past_step, double delay_action_step, int horizon,
    const std::vector<int>& terminal_noise_levels = {}) {
    if (past_step < 0)
        throw std::invalid_argument("past_step must be >= 0");
    if (!std::isfinite(delay_action_step))
        throw std::invalid_argument("delay_action_step must be finite");
    if (horizon <= 1)
        throw std::invalid_argument("horizon must be > 1");

    const double coordinate = static_cast<double>(past_step) + delay_action_step;
    const double lower_d = std::floor(coordinate);
    const double upper_d = std::ceil(coordinate);
    if (!std::isfinite(coordinate) || lower_d < 0.0 || upper_d >= horizon - 1) {
        throw std::out_of_range(
            "action interpolation endpoints are outside executable slots: coordinate=" +
            std::to_string(coordinate) + ", executable=[0, " +
            std::to_string(horizon - 2) + "], horizon=" + std::to_string(horizon));
    }
    const int lower = static_cast<int>(lower_d);
    const int upper = static_cast<int>(upper_d);
    const bool fractional = lower != upper;
    int lower_noise = 0;
    int upper_noise = 0;
    if (terminal_noise_levels.empty()) {
        if (fractional)
            throw std::invalid_argument(
                "fractional delay_action_step requires terminal action-noise levels");
    } else {
        if (terminal_noise_levels.size() != static_cast<size_t>(horizon))
            throw std::invalid_argument(
                "terminal action-noise level count must equal horizon");
        lower_noise = terminal_noise_levels[static_cast<size_t>(lower)];
        upper_noise = terminal_noise_levels[static_cast<size_t>(upper)];
        if (lower_noise != 0 || upper_noise != 0)
            throw std::invalid_argument(
                "delay_action_step requires terminally clean selected "
                "endpoints; lower=" + std::to_string(lower) + " noise=" +
                std::to_string(lower_noise) + ", upper=" +
                std::to_string(upper) + " noise=" + std::to_string(upper_noise));
    }
    return {lower, upper, coordinate - lower_d, lower_noise, upper_noise};
}

inline ActionSelection runner_action_selection(
    int n_obs_steps, double delay_action_step, int horizon,
    const std::vector<int>& terminal_noise_levels = {}) {
    if (n_obs_steps <= 0)
        throw std::invalid_argument("n_obs_steps must be > 0");
    return action_selection(
        n_obs_steps - 1, delay_action_step, horizon, terminal_noise_levels);
}

inline int selected_action_index(int past_step, double delay_action_step, int horizon) {
    const auto s = action_selection(past_step, delay_action_step, horizon);
    if (s.lower_index != s.upper_index)
        throw std::invalid_argument(
            "selected_action_index requires an integral selected coordinate");
    return s.lower_index;
}

inline int runner_action_index(int n_obs_steps, double delay_action_step, int horizon) {
    const auto s = runner_action_selection(n_obs_steps, delay_action_step, horizon);
    if (s.lower_index != s.upper_index)
        throw std::invalid_argument(
            "runner_action_index requires an integral selected coordinate");
    return s.lower_index;
}

}  // namespace diffusion_deploy
