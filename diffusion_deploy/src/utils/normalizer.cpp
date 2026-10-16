#include "diffusion_deploy/utils/normalizer.hpp"
#include <stdexcept>

namespace diffusion_deploy {

// ---- Normalizer ----

Normalizer::Normalizer(torch::Tensor scale, torch::Tensor offset, Mode mode)
    : scale_(std::move(scale)), offset_(std::move(offset)), mode_(mode) {}

std::shared_ptr<Normalizer> Normalizer::create_identity(int dim, torch::Dtype dtype) {
    auto scale  = torch::ones(dim, dtype);
    auto offset = torch::zeros(dim, dtype);
    return std::make_shared<Normalizer>(scale, offset, Mode::LINEAR);
}

std::shared_ptr<Normalizer> Normalizer::from_scale_offset(
    const std::vector<float>& scale,
    const std::vector<float>& offset)
{
    if (scale.size() != offset.size())
        throw std::invalid_argument("Normalizer::from_scale_offset: scale and offset size mismatch");
    return std::make_shared<Normalizer>(torch::tensor(scale), torch::tensor(offset), Mode::LINEAR);
}

std::shared_ptr<Normalizer> Normalizer::from_min_max(
    const std::vector<float>& input_min,
    const std::vector<float>& input_max,
    float output_min,
    float output_max)
{
    const int D = static_cast<int>(input_min.size());
    if (static_cast<int>(input_max.size()) != D)
        throw std::invalid_argument("Normalizer::from_min_max: min and max size mismatch");

    auto t_min = torch::tensor(input_min);
    auto t_max = torch::tensor(input_max);

    // Avoid division by zero for constant dims
    constexpr float range_eps = 1e-4f;
    auto range = t_max - t_min;
    auto ignore = range.abs() < range_eps;
    range.index_put_({ignore}, (output_max - output_min));

    auto scale  = torch::full({D}, (output_max - output_min)) / range;
    auto offset = torch::full({D}, static_cast<float>(output_min)) - scale * t_min;
    // constant dims: center at midpoint
    auto mid = (output_max + output_min) / 2.0f;
    offset.index_put_({ignore}, mid - t_min.index({ignore}));

    return std::make_shared<Normalizer>(scale, offset, Mode::LINEAR);
}

std::shared_ptr<Normalizer> Normalizer::from_mean_std(
    const std::vector<float>& mean,
    const std::vector<float>& std)
{
    const int D = static_cast<int>(mean.size());
    if (static_cast<int>(std.size()) != D)
        throw std::invalid_argument("Normalizer::from_mean_std: mean and std size mismatch");

    constexpr float range_eps = 1e-4f;
    auto t_std  = torch::tensor(std);
    auto t_mean = torch::tensor(mean);

    auto ignore = t_std.abs() < range_eps;
    auto std_safe = t_std.clone();
    std_safe.index_put_({ignore}, 1.0f);

    auto scale  = 1.0f / std_safe;
    auto offset = -t_mean * scale;
    return std::make_shared<Normalizer>(scale, offset, Mode::GAUSSIAN);
}

torch::Tensor Normalizer::normalize(const torch::Tensor& x) const {
    auto src_shape = x.sizes().vec();
    auto scale = scale_.to(x.device());
    auto offset = offset_.to(x.device());
    auto xf = x.to(scale.dtype()).reshape({-1, scale.size(0)});
    auto y  = xf * scale + offset;
    return y.reshape(src_shape);
}

torch::Tensor Normalizer::unnormalize(const torch::Tensor& y) const {
    auto src_shape = y.sizes().vec();
    auto scale = scale_.to(y.device());
    auto offset = offset_.to(y.device());
    auto yf = y.to(scale.dtype()).reshape({-1, scale.size(0)});
    auto x  = (yf - offset) / scale;
    return x.reshape(src_shape);
}

Normalizer& Normalizer::to(torch::Device device) {
    scale_  = scale_.to(device);
    offset_ = offset_.to(device);
    return *this;
}

// ---- MultiNormalizer ----

void MultiNormalizer::add(const std::string& key, std::shared_ptr<Normalizer> normalizer) {
    normalizers_[key] = std::move(normalizer);
}

bool MultiNormalizer::has(const std::string& key) const {
    return normalizers_.count(key) > 0;
}

const std::shared_ptr<Normalizer>& MultiNormalizer::get(const std::string& key) const {
    auto it = normalizers_.find(key);
    if (it == normalizers_.end())
        throw std::out_of_range("MultiNormalizer: key not found: " + key);
    return it->second;
}

std::shared_ptr<Normalizer>& MultiNormalizer::get(const std::string& key) {
    auto it = normalizers_.find(key);
    if (it == normalizers_.end())
        throw std::out_of_range("MultiNormalizer: key not found: " + key);
    return it->second;
}

torch::Tensor MultiNormalizer::normalize(const std::string& key, const torch::Tensor& x) const {
    return get(key)->normalize(x);
}

torch::Tensor MultiNormalizer::unnormalize(const std::string& key, const torch::Tensor& x) const {
    return get(key)->unnormalize(x);
}

MultiNormalizer& MultiNormalizer::to(torch::Device device) {
    for (auto& [key, norm] : normalizers_)
        norm->to(device);
    return *this;
}

}  // namespace diffusion_deploy
