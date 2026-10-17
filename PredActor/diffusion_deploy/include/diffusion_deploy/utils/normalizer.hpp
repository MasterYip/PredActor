/**
 * normalizer.hpp
 *
 * Linear normalizer matching Python diffusion_policy.utils.normalizer.
 *
 * Python normalizer formula (mode='limits'):
 *   normalized = x * scale + offset
 *   unnormalized = (x - offset) / scale
 *
 * where scale and offset are fit from training data such that:
 *   output ∈ [output_min, output_max]  (default [-1, 1])
 *
 * Stats are exported from the Python checkpoint and loaded from YAML.
 */
#pragma once

#include <memory>
#include <string>
#include <unordered_map>
#include <torch/torch.h>

namespace diffusion_deploy {

/**
 * Single-field normalizer.
 * Mirrors Python SingleFieldLinearNormalizer.
 */
class Normalizer {
public:
    enum class Mode { LINEAR, GAUSSIAN };

    /**
     * Construct from scale/offset tensors.
     *
     * normalized = x * scale + offset
     * unnormalized = (x - offset) / scale
     */
    Normalizer(torch::Tensor scale, torch::Tensor offset, Mode mode = Mode::LINEAR);

    /**
     * Create an identity normalizer (scale=1, offset=0).
     * Useful as a no-op placeholder.
     */
    static std::shared_ptr<Normalizer> create_identity(int dim, torch::Dtype dtype = torch::kFloat32);

    /**
     * Create directly from scale/offset arrays (mode=LINEAR).
     * normalized = x * scale + offset
     */
    static std::shared_ptr<Normalizer> from_scale_offset(
        const std::vector<float>& scale,
        const std::vector<float>& offset);

    /**
     * Create from min/max arrays (mode=LINEAR, output_min=-1, output_max=1).
     *
     * scale  = (output_max - output_min) / (input_max - input_min)
     * offset = output_min - scale * input_min
     */
    static std::shared_ptr<Normalizer> from_min_max(
        const std::vector<float>& input_min,
        const std::vector<float>& input_max,
        float output_min = -1.0f,
        float output_max =  1.0f);

    /**
     * Create from mean/std arrays (mode=GAUSSIAN).
     *
     * scale  = 1 / std
     * offset = -mean / std
     */
    static std::shared_ptr<Normalizer> from_mean_std(
        const std::vector<float>& mean,
        const std::vector<float>& std);

    /**
     * Normalize: y = x * scale + offset
     * Input shape: [..., D] — last dim is normalized independently.
     */
    torch::Tensor normalize(const torch::Tensor& x) const;

    /**
     * Unnormalize: x = (y - offset) / scale
     */
    torch::Tensor unnormalize(const torch::Tensor& y) const;

    int dim() const { return static_cast<int>(scale_.size(0)); }

    const torch::Tensor& scale()  const { return scale_; }
    const torch::Tensor& offset() const { return offset_; }

    /** Move tensors to device. */
    Normalizer& to(torch::Device device);

private:
    torch::Tensor scale_;   // [D]
    torch::Tensor offset_;  // [D]
    Mode mode_;
};

/**
 * Multi-field normalizer keyed by string.
 * Mirrors Python LinearNormalizer.
 *
 * Typical keys: "obs", "action", "cond"
 */
class MultiNormalizer {
public:
    void add(const std::string& key, std::shared_ptr<Normalizer> normalizer);
    bool has(const std::string& key) const;

    const std::shared_ptr<Normalizer>& get(const std::string& key) const;
    std::shared_ptr<Normalizer>&       get(const std::string& key);

    /** Convenience: normalize a tensor by key. */
    torch::Tensor normalize(const std::string& key, const torch::Tensor& x) const;

    /** Convenience: unnormalize a tensor by key. */
    torch::Tensor unnormalize(const std::string& key, const torch::Tensor& x) const;

    /** Move all normalizers to device. */
    MultiNormalizer& to(torch::Device device);

private:
    std::unordered_map<std::string, std::shared_ptr<Normalizer>> normalizers_;
};

}  // namespace diffusion_deploy
