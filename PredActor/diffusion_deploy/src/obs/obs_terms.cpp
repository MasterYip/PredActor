#include "diffusion_deploy/obs/obs_terms.hpp"

namespace diffusion_deploy {

ObsTensorMap obs_terms_to_map(const ObsTerms& t) {
    ObsTensorMap m;
    auto insert = [&](const std::string& key, const torch::Tensor& tensor) {
        if (tensor.defined()) m[key] = tensor;
    };
    insert("body_pos",          t.body_pos);
    insert("body_rot",          t.body_rot);
    insert("body_lin_vel",      t.body_lin_vel);
    insert("body_ang_vel",      t.body_ang_vel);
    insert("root_pos",          t.root_pos);
    insert("root_rot",          t.root_rot);
    insert("joint_pos",         t.joint_pos);
    insert("joint_vel",         t.joint_vel);
    insert("projected_gravity", t.projected_gravity);
    insert("base_lin_vel",      t.base_lin_vel);
    insert("base_ang_vel",      t.base_ang_vel);
    insert("last_actions",      t.last_actions);
    return m;
}

ObsTerms obs_terms_from_map(const ObsTensorMap& m) {
    ObsTerms t;
    auto get = [&](const std::string& key) -> torch::Tensor {
        auto it = m.find(key);
        return (it != m.end()) ? it->second : torch::Tensor{};
    };
    t.body_pos          = get("body_pos");
    t.body_rot          = get("body_rot");
    t.body_lin_vel      = get("body_lin_vel");
    t.body_ang_vel      = get("body_ang_vel");
    t.root_pos          = get("root_pos");
    t.root_rot          = get("root_rot");
    t.joint_pos         = get("joint_pos");
    t.joint_vel         = get("joint_vel");
    t.projected_gravity = get("projected_gravity");
    t.base_lin_vel      = get("base_lin_vel");
    t.base_ang_vel      = get("base_ang_vel");
    t.last_actions      = get("last_actions");
    return t;
}

}  // namespace diffusion_deploy
