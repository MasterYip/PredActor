#include <ATen/Parallel.h>
#include <ATen/Version.h>
#include <torch/script.h>
#include <torch/torch.h>
#include <torch/version.h>

#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs = std::filesystem;

namespace {

std::string argument(int argc, char* argv[], const std::string& flag) {
    for (int i = 1; i + 1 < argc; ++i)
        if (std::string(argv[i]) == flag) return argv[i + 1];
    return {};
}

torch::Tensor load_fixture(const fs::path& path, const torch::Device& device) {
    auto module = torch::jit::load(path.string(), device);
    return module.attr("0").toTensor().to(device).contiguous().clone();
}

}  // namespace

int main(int argc, char* argv[]) {
    const auto graph_path = argument(argc, argv, "--graph");
    const auto fixture_path = argument(argc, argv, "--fixtures");
    const auto count_text = argument(argc, argv, "--n-cases");
    if (graph_path.empty() || fixture_path.empty() || count_text.empty()) {
        std::cerr << "usage: audit_backbone_runtime --graph PATH --fixtures DIR "
                     "--n-cases N [--device cpu]\n";
        return 2;
    }
    const auto device_text = argument(argc, argv, "--device");
    const torch::Device device(device_text.empty() ? "cpu" : device_text);
    const int count = std::stoi(count_text);

    std::cout << "[backbone-audit] torch_version=" << TORCH_VERSION
              << " intra_op_threads=" << at::get_num_threads()
              << " interop_threads=" << at::get_num_interop_threads() << "\n"
              << at::show_config() << "\n";

    torch::NoGradGuard no_grad;
    auto graph = torch::jit::load(graph_path, device);
    graph.eval();
    const fs::path fixtures(fixture_path);
    for (int index = 0; index < count; ++index) {
        const auto prefix = fixtures / ("case_" + std::to_string(index) + "_");
        std::vector<torch::jit::IValue> inputs;
        for (const char* suffix : {"state_input.pt", "action_input.pt", "state_t.pt",
                                   "action_t.pt", "cond.pt"})
            inputs.emplace_back(load_fixture(prefix.string() + suffix, device));
        const auto result = graph.forward(inputs).toTuple()->elements();
        if (result.size() != 2 || !result[0].isTensor() || !result[1].isTensor())
            throw std::runtime_error("backbone forward must return two tensors");
        torch::save(result[0].toTensor().cpu().contiguous(),
                    prefix.string() + "cpp_state_output.pt");
        torch::save(result[1].toTensor().cpu().contiguous(),
                    prefix.string() + "cpp_action_output.pt");
    }
    std::cout << "[backbone-audit] completed_cases=" << count << "\n";
    return 0;
}
