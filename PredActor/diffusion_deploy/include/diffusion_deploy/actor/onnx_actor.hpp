/**
 * onnx_actor.hpp
 *
 * ONNXRuntime actor backend.
 * Implements the same BaseActor interface as TorchActor.
 *
 * Requires compilation with USE_ONNX=ON and onnxruntime installed.
 * The ONNX model must be a full-loop export (single forward call).
 */
#pragma once

#include "diffusion_deploy/actor/base_actor.hpp"
#include <string>
#include <memory>
#include <vector>

#ifdef USE_ONNX
#include <onnxruntime_cxx_api.h>
#endif

namespace diffusion_deploy {

class OnnxActor : public BaseActor {
public:
    /**
     * Load an ONNX model.
     *
     * Expected model I/O:
     *   input[0]:  "obs"   float32 [B, n_obs_steps, obs_dim]
     *   input[1]:  "cond"  float32 [B, 1, cond_dim]  (optional)
     *   output[0]: "action_traj" float32 [B, horizon, action_dim]
     */
    OnnxActor(const std::string& model_path,
              const ActorConfig& config,
              bool use_cuda = false);

    torch::Tensor act(const torch::Tensor& nobs_norm,
                       const torch::Tensor& cond_norm = {}) override;

    int n_obs_steps()    const override { return config_.n_obs_steps; }
    int n_future_steps() const override { return config_.n_future_steps; }
    int horizon()        const override { return config_.horizon(); }
    int action_dim()     const override { return config_.action_dim; }
    int obs_dim()        const override { return config_.obs_dim; }

    torch::Device device() const override { return device_; }
    void to(torch::Device device) override { device_ = device; }

private:
    ActorConfig config_;
    torch::Device device_{torch::kCPU};

#ifdef USE_ONNX
    Ort::Env env_{ORT_LOGGING_LEVEL_WARNING, "OnnxActor"};
    Ort::SessionOptions session_options_;
    std::unique_ptr<Ort::Session> session_;
    Ort::AllocatorWithDefaultOptions allocator_;

    std::vector<const char*> input_names_;
    std::vector<const char*> output_names_;

    /** Run ORT session; convert tensor to/from ORT format. */
    torch::Tensor run_session(const std::vector<torch::Tensor>& inputs);
#endif
};

}  // namespace diffusion_deploy
