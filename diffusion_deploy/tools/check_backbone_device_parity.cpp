/** Identical-input CPU/CUDA parity for an exported joint TorchScript backbone. */
#include <torch/script.h>
#include <torch/torch.h>

#include <algorithm>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <string>
#include <tuple>
#include <vector>

namespace {

std::string arg(int argc, char** argv, const std::string& key,
                const std::string& fallback = {}) {
    for (int i = 1; i + 1 < argc; ++i)
        if (argv[i] == key) return argv[i + 1];
    return fallback;
}

using Output = std::pair<torch::Tensor, torch::Tensor>;

Output output_pair(const torch::jit::IValue& value) {
    if (!value.isTuple() || value.toTuple()->elements().size() != 2)
        throw std::runtime_error("backbone output must be a two-tensor tuple");
    const auto& elements = value.toTuple()->elements();
    return {elements[0].toTensor(), elements[1].toTensor()};
}

Output direct(torch::jit::script::Module& module,
              const std::vector<torch::Tensor>& values) {
    std::vector<torch::jit::IValue> inputs(values.begin(), values.end());
    return output_pair(module.forward(inputs));
}

Output encoded(torch::jit::script::Module& module,
               const std::vector<torch::Tensor>& values) {
    auto memory = module.get_method("build_condition_embeddings")(
        {values.at(4)}).toTensor();
    std::vector<torch::jit::IValue> inputs{
        values.at(0), values.at(1), values.at(2), values.at(3), memory};
    return output_pair(module.get_method("forward_encoded_condition")(inputs));
}

double max_abs(const Output& left, const Output& right) {
    return std::max(
        (left.first.cpu() - right.first.cpu()).abs().max().item<double>(),
        (left.second.cpu() - right.second.cpu()).abs().max().item<double>());
}

bool finite(const Output& value) {
    return torch::isfinite(value.first).all().item<bool>()
        && torch::isfinite(value.second).all().item<bool>();
}

}  // namespace

int main(int argc, char** argv) {
    try {
        torch::InferenceMode inference_guard;
        const auto model_path = arg(argc, argv, "--model");
        const auto output_path = arg(argc, argv, "--output");
        const double tolerance = std::stod(arg(argc, argv, "--atol", "1e-4"));
        const int cond_dim = std::stoi(arg(argc, argv, "--cond-dim", "605"));
        const int horizon = std::stoi(arg(argc, argv, "--horizon", "16"));
        if (model_path.empty() || output_path.empty() || tolerance <= 0.0
            || cond_dim <= 0 || horizon <= 0)
            throw std::invalid_argument(
                "requires --model, --output, --atol > 0, --cond-dim > 0 "
                "and --horizon > 0");
        if (!torch::cuda::is_available())
            throw std::runtime_error("CUDA is unavailable");

        auto cpu_module = torch::jit::load(model_path, torch::Device(torch::kCPU));
        auto cuda_module = torch::jit::load(model_path, torch::Device(torch::kCUDA, 0));
        cpu_module.eval();
        cuda_module.eval();
        const bool cpu_has_encoded = cpu_module.find_method(
            "build_condition_embeddings").has_value()
            && cpu_module.find_method("forward_encoded_condition").has_value();
        const bool cuda_has_encoded = cuda_module.find_method(
            "build_condition_embeddings").has_value()
            && cuda_module.find_method("forward_encoded_condition").has_value();
        if (cpu_has_encoded != cuda_has_encoded)
            throw std::runtime_error(
                "CPU and CUDA modules expose different condition APIs");
        const bool has_encoded = cpu_has_encoded;

        struct Record {
            int seed;
            double cpu_encoded;
            double cuda_encoded;
            double direct_device;
            double encoded_device;
            bool all_finite;
        };
        std::vector<Record> records;
        double maximum = 0.0;
        for (const int seed : {85043, 85044, 85045}) {
            torch::manual_seed(seed);
            const auto float_options = torch::TensorOptions().dtype(torch::kFloat32);
            const auto long_options = torch::TensorOptions().dtype(torch::kLong);
            std::vector<torch::Tensor> cpu_inputs{
                torch::randn({1, horizon, 384}, float_options),
                torch::randn({1, horizon, 29}, float_options),
                torch::randint(0, 20, {1, horizon}, long_options),
                torch::randint(0, 20, {1, horizon}, long_options),
                torch::randn({1, 4, cond_dim}, float_options),
            };
            std::vector<torch::Tensor> cuda_inputs;
            cuda_inputs.reserve(cpu_inputs.size());
            for (const auto& input : cpu_inputs) cuda_inputs.push_back(input.cuda());

            const auto cpu_direct = direct(cpu_module, cpu_inputs);
            const auto cuda_direct = direct(cuda_module, cuda_inputs);
            const double not_applicable = std::numeric_limits<double>::quiet_NaN();
            double cpu_encoded_error = not_applicable;
            double cuda_encoded_error = not_applicable;
            double encoded_device_error = not_applicable;
            bool all_finite = finite(cpu_direct) && finite(cuda_direct);
            if (has_encoded) {
                const auto cpu_encoded = encoded(cpu_module, cpu_inputs);
                const auto cuda_encoded = encoded(cuda_module, cuda_inputs);
                cpu_encoded_error = max_abs(cpu_direct, cpu_encoded);
                cuda_encoded_error = max_abs(cuda_direct, cuda_encoded);
                encoded_device_error = max_abs(cpu_encoded, cuda_encoded);
                all_finite = all_finite && finite(cpu_encoded)
                    && finite(cuda_encoded);
            }
            Record record{
                seed,
                cpu_encoded_error,
                cuda_encoded_error,
                max_abs(cpu_direct, cuda_direct),
                encoded_device_error,
                all_finite,
            };
            maximum = std::max(maximum, record.direct_device);
            if (has_encoded)
                maximum = std::max(maximum, record.encoded_device);
            records.push_back(record);
        }

        const bool passed = maximum <= tolerance
            && std::all_of(records.begin(), records.end(),
                           [](const Record& value) { return value.all_finite; });
        std::ofstream output(output_path);
        if (!output) throw std::runtime_error("cannot open output: " + output_path);
        output << std::setprecision(10)
               << "schema,status,seed,horizon,cond_dim,condition_api,"
                  "cpu_direct_encoded_max_abs,"
                  "cuda_direct_encoded_max_abs,cpu_cuda_direct_max_abs,"
                  "cpu_cuda_encoded_max_abs,finite,atol\n";
        for (const auto& record : records) {
            output << "task085-backbone-device-parity-v1,"
                   << (passed ? "pass" : "fail") << ',' << record.seed << ','
                   << horizon << ',' << cond_dim << ','
                   << (has_encoded ? "encoded" : "direct-only") << ','
                   << record.cpu_encoded << ',' << record.cuda_encoded << ','
                   << record.direct_device << ',' << record.encoded_device << ','
                   << (record.all_finite ? "true" : "false") << ','
                   << tolerance << '\n';
        }
        std::cout << "[" << (passed ? "PASS" : "FAIL")
                  << "] identical-input CPU/CUDA backbone parity max_abs="
                  << maximum << " atol=" << tolerance << '\n';
        return passed ? 0 : 1;
    } catch (const std::exception& error) {
        std::cerr << "[FAIL] backbone device parity: " << error.what() << '\n';
        return 1;
    }
}
