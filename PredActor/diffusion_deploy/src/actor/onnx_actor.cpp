#include "diffusion_deploy/actor/onnx_actor.hpp"
#include <stdexcept>
#include <iostream>

namespace diffusion_deploy {

#ifdef USE_ONNX

OnnxActor::OnnxActor(const std::string& model_path,
                     const ActorConfig& config,
                     bool use_cuda)
    : config_(config)
{
    session_options_.SetIntraOpNumThreads(1);
    session_options_.SetGraphOptimizationLevel(ORT_ENABLE_ALL);

    if (use_cuda) {
        OrtCUDAProviderOptions cuda_opts;
        session_options_.AppendExecutionProvider_CUDA(cuda_opts);
        device_ = torch::kCUDA;
    }

    session_ = std::make_unique<Ort::Session>(env_,
        model_path.c_str(), session_options_);

    // Collect input/output names
    size_t n_in  = session_->GetInputCount();
    size_t n_out = session_->GetOutputCount();
    for (size_t i = 0; i < n_in;  ++i)
        input_names_.push_back(session_->GetInputNameAllocated(i, allocator_).get());
    for (size_t i = 0; i < n_out; ++i)
        output_names_.push_back(session_->GetOutputNameAllocated(i, allocator_).get());

    std::cout << "[OnnxActor] Loaded: " << model_path
              << " (" << n_in << " inputs, " << n_out << " outputs)\n";
}

torch::Tensor OnnxActor::act(const torch::Tensor& nobs_norm,
                              const torch::Tensor& cond_norm) {
    torch::NoGradGuard ng;

    std::vector<torch::Tensor> inputs;
    inputs.push_back(nobs_norm.to(torch::kCPU).to(torch::kFloat32).contiguous());
    if (cond_norm.defined() && cond_norm.numel() > 0 && input_names_.size() > 1) {
        inputs.push_back(cond_norm.to(torch::kCPU).to(torch::kFloat32).contiguous());
    }
    return run_session(inputs);
}

torch::Tensor OnnxActor::run_session(const std::vector<torch::Tensor>& inputs) {
    auto memory_info = Ort::MemoryInfo::CreateCpu(
        OrtArenaAllocator, OrtMemTypeDefault);

    std::vector<Ort::Value> ort_inputs;
    for (const auto& t : inputs) {
        auto shape = t.sizes().vec();
        std::vector<int64_t> shape64(shape.begin(), shape.end());
        ort_inputs.emplace_back(Ort::Value::CreateTensor<float>(
            memory_info,
            const_cast<float*>(t.data_ptr<float>()),
            t.numel(),
            shape64.data(),
            shape64.size()));
    }

    auto ort_outputs = session_->Run(
        Ort::RunOptions{nullptr},
        input_names_.data(),
        ort_inputs.data(),
        ort_inputs.size(),
        output_names_.data(),
        output_names_.size());

    // First output is action_traj
    const auto& info = ort_outputs[0].GetTensorTypeAndShapeInfo();
    auto shape = info.GetShape();
    std::vector<int64_t> shape64(shape.begin(), shape.end());

    auto result = torch::from_blob(
        ort_outputs[0].GetTensorMutableData<float>(),
        shape64, torch::kFloat32).clone();

    return result;
}

#else  // !USE_ONNX

OnnxActor::OnnxActor(const std::string& /*model_path*/,
                     const ActorConfig& config,
                     bool /*use_cuda*/)
    : config_(config)
{
    throw std::runtime_error(
        "[OnnxActor] Built without USE_ONNX. Recompile with -DUSE_ONNX=ON.");
}

torch::Tensor OnnxActor::act(const torch::Tensor&, const torch::Tensor&) {
    throw std::runtime_error("[OnnxActor] Not available (USE_ONNX=OFF).");
}

#endif  // USE_ONNX

}  // namespace diffusion_deploy
