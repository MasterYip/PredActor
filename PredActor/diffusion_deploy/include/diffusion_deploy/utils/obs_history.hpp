/**
 * obs_history.hpp
 *
 * Temporal history ring buffer for raw observation terms.
 *
 * Mirrors the stateless Python helpers:
 *   ObsComposer.init_history(terms, n_obs_steps)
 *   ObsComposer.shift_append(history, latest_terms)
 *
 * Usage:
 *   ObsHistory history(n_obs_steps);
 *   history.init(first_terms_map);          // repeated n_obs_steps times
 *   history.shift_append(new_terms_map);    // drop oldest, append latest
 *   auto& hist = history.get();             // ObsTensorMap with T=n_obs_steps
 */
#pragma once

#include "diffusion_deploy/obs/obs_terms.hpp"
#include <stdexcept>

namespace diffusion_deploy {

class ObsHistory {
public:
    explicit ObsHistory(int n_obs_steps);

    /**
     * Initialise history by repeating a single-timestep (T=1) snapshot.
     * Mirrors ObsComposer.init_history() in Python.
     *
     * After this call, every tensor in history has shape [B, n_obs_steps, ...].
     */
    void init(const ObsTensorMap& terms);

    /**
     * Shift history left and append the latest T=1 snapshot.
     * Mirrors ObsComposer.shift_append() in Python.
     *
     *   history[:, 0:T-1] = history[:, 1:T]
     *   history[:, T-1]   = latest
     */
    void shift_append(const ObsTensorMap& latest);

    /** Return the current history map. Each tensor: [B, n_obs_steps, ...]. */
    const ObsTensorMap& get() const { return history_; }

    bool initialized() const { return initialized_; }
    int n_obs_steps() const { return n_obs_steps_; }

private:
    int n_obs_steps_;
    bool initialized_ = false;
    ObsTensorMap history_;
};

}  // namespace diffusion_deploy
