/** Non-actuating NS-DDIM fast-WBG NFE, parity, determinism, and timing gate. */
#include "diffusion_deploy/actor/diffuse_cloc_actor.hpp"
#include "diffusion_deploy/utils/config_parser.hpp"

#include <torch/torch.h>
#include <algorithm>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs = std::filesystem;
using Clock = std::chrono::steady_clock;

namespace {

std::string argument(int argc, char** argv, const std::string& key,
                     const std::string& fallback = {}) {
    for (int i = 1; i + 1 < argc; ++i)
        if (argv[i] == key) return argv[i + 1];
    return fallback;
}

void synchronize(const torch::Device& device) {
    if (device.is_cuda()) torch::cuda::synchronize(device.index());
}

double median(std::vector<double> values) {
    std::sort(values.begin(), values.end());
    const auto middle = values.size() / 2;
    return values.size() % 2 ? values[middle]
                             : 0.5 * (values[middle - 1] + values[middle]);
}

struct Candidate {
    std::string name;
    std::string guidance_impl;
    std::string axis_impl;
    std::uint64_t expected_nfe;
};

struct Result {
    torch::Tensor output;
    std::uint64_t nfe = 0;
    double deterministic_max_abs = 0.0;
    double median_wall_ms = 0.0;
};

std::shared_ptr<diffusion_deploy::DiffuseCLoCActor> make_actor(
    diffusion_deploy::DeployConfig cfg, const Candidate& candidate,
    const torch::Device& device) {
    cfg.cloc_actor.sampler_mode = "ns_ddim";
    cfg.cloc_actor.use_ns_ddim = true;
    cfg.cloc_actor.ddim_steps = 2;
    cfg.cloc_actor.ddim_eta = 0.0f;
    cfg.cloc_actor.no_state_override = true;
    cfg.cloc_actor.randomize_noise_schedule = true;
    cfg.cloc_actor.classifier_guidance_impl = candidate.guidance_impl;
    cfg.cloc_actor.guidance.enabled = true;
    cfg.cloc_actor.guidance.axis_gradient_impl = candidate.axis_impl;
    auto actor = std::make_shared<diffusion_deploy::DiffuseCLoCActor>(
        cfg.model_path, cfg.schedule_path, cfg.cloc_actor.emphasis_path,
        cfg.cloc_actor, device);
    diffusion_deploy::WbgUdpFrame frame;
    frame.vx_enabled = frame.vy_enabled = frame.wz_enabled = 1.0f;
    frame.vx_command = 0.7f;
    frame.vy_command = -0.2f;
    frame.wz_command = 0.4f;
    frame.vx_kp = frame.vy_kp = frame.wz_kp = 1.0f;
    actor->apply_live_wbg(frame);
    return actor;
}

torch::Tensor checked_act(diffusion_deploy::DiffuseCLoCActor& actor,
                          const torch::Tensor& obs,
                          const torch::Tensor& condition,
                          const torch::Device& device,
                          int seed, std::uint64_t expected_nfe) {
    actor.reset();
    actor.reset_backbone_forward_count();
    torch::manual_seed(seed);
    auto output = actor.act(obs, condition);
    synchronize(device);
    const auto nfe = actor.backbone_forward_count();
    if (nfe != expected_nfe)
        throw std::runtime_error(
            "NFE gate failed: expected " + std::to_string(expected_nfe)
            + ", observed " + std::to_string(nfe));
    if (!torch::isfinite(output).all().item<bool>())
        throw std::runtime_error("nonfinite policy output");
    return output;
}

}  // namespace

int main(int argc, char** argv) {
    try {
        torch::InferenceMode inference_guard;
        const std::string config_path = argument(argc, argv, "--config");
        const fs::path output_path = argument(argc, argv, "--output");
        const torch::Device device(argument(argc, argv, "--device", "cpu"));
        const int warmup = std::stoi(argument(argc, argv, "--warmup", "2"));
        const int repetitions = std::stoi(argument(argc, argv, "--repetitions", "10"));
        const int seed = std::stoi(argument(argc, argv, "--seed", "20260912"));
        if (config_path.empty() || output_path.empty() || warmup < 1 || repetitions < 2)
            throw std::invalid_argument(
                "requires --config, --output, warmup>=1, repetitions>=2");
        if (device.is_cuda() && !torch::cuda::is_available())
            throw std::runtime_error("CUDA unavailable");

        const auto cfg = diffusion_deploy::load_config(config_path);
        if (cfg.actor_type != "prdp" || cfg.cloc_actor.sampler_mode != "ns_ddim"
            || cfg.cloc_actor.ddim_steps != 2 || !cfg.cloc_actor.use_ns_ddim
            || !cfg.cloc_actor.no_state_override
            || cfg.cloc_actor.classifier_guidance_impl != "reuse_x0"
            || !cfg.cloc_actor.guidance.enabled)
            throw std::invalid_argument(
                "config must select PRDP NS-DDIM2 no_state_override reuse_x0 WBG");

        const auto options = torch::TensorOptions().dtype(torch::kFloat32).device(device);
        torch::manual_seed(seed);
        const auto obs = torch::empty(
            {1, cfg.cloc_actor.n_obs_steps, cfg.cloc_actor.obs_dim}, options)
                             .uniform_(-1.0f, 1.0f);
        const auto condition = torch::empty(
            {1, cfg.cloc_actor.n_cond_steps, cfg.cloc_actor.backbone_cond_dim}, options)
                                   .uniform_(-1.0f, 1.0f);

        const std::vector<Candidate> candidates{
            {"reuse_sequential", "reuse_x0", "sequential", 2},
            {"reuse_stacked", "reuse_x0", "stacked", 2},
            {"legacy_duplicate_sequential", "duplicate_backbone", "sequential", 4},
        };
        std::map<std::string, Result> results;
        for (const auto& candidate : candidates) {
            auto actor = make_actor(cfg, candidate, device);
            (void)checked_act(*actor, obs, condition, device, seed + 1,
                              candidate.expected_nfe);
            auto first = checked_act(*actor, obs, condition, device, seed + 2,
                                     candidate.expected_nfe);
            auto second = checked_act(*actor, obs, condition, device, seed + 2,
                                      candidate.expected_nfe);
            const double deterministic_max_abs =
                (first - second).abs().max().item<double>();
            if (deterministic_max_abs != 0.0)
                throw std::runtime_error(candidate.name + " is nondeterministic");
            std::vector<double> samples;
            for (int i = 0; i < warmup + repetitions; ++i) {
                const auto begin = Clock::now();
                (void)checked_act(*actor, obs, condition, device, seed + 3,
                                  candidate.expected_nfe);
                const auto end = Clock::now();
                if (i >= warmup)
                    samples.push_back(std::chrono::duration<double, std::milli>(
                        end - begin).count());
            }
            results.emplace(candidate.name, Result{
                first.to(torch::kCPU), candidate.expected_nfe,
                deterministic_max_abs, median(samples)});
        }

        const double stacked_parity = (
            results.at("reuse_stacked").output
            - results.at("reuse_sequential").output).abs().max().item<double>();
        constexpr double kStackedTolerance = 2e-5;
        if (stacked_parity > kStackedTolerance)
            throw std::runtime_error(
                "stacked/sequential reuse_x0 parity failed: max_abs="
                + std::to_string(stacked_parity));
        const double legacy_drift = (
            results.at("legacy_duplicate_sequential").output
            - results.at("reuse_sequential").output).abs().max().item<double>();

        fs::create_directories(output_path.parent_path());
        std::ofstream output(output_path);
        output << "candidate,status,nfe,finite,deterministic_max_abs,median_wall_ms,"
                  "stacked_reuse_max_abs,stacked_tolerance,legacy_drift_max_abs\n";
        for (const auto& candidate : candidates) {
            const auto& result = results.at(candidate.name);
            output << std::setprecision(10) << candidate.name << ",pass,"
                   << result.nfe << ",true," << result.deterministic_max_abs << ','
                   << result.median_wall_ms << ',' << stacked_parity << ','
                   << kStackedTolerance << ',' << legacy_drift << '\n';
        }
        std::cout << std::setprecision(10)
                  << "[PASS] NS-DDIM2 fast WBG: NFE=2; stacked/sequential max_abs="
                  << stacked_parity << " <= " << kStackedTolerance
                  << "; legacy drift diagnostic=" << legacy_drift
                  << "; reuse_stacked median="
                  << results.at("reuse_stacked").median_wall_ms << " ms\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "[FAIL] NS-DDIM fast WBG gate: " << error.what() << '\n';
        return 1;
    }
}
