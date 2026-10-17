/**
 * csv_recorder.hpp
 *
 * Opt-in per-control-step recording for deployment diagnostics.  The recorder
 * is constructed only when a CSV path is supplied, so the normal deployment
 * path does not allocate, format, or write recording data.
 */
#pragma once

#include "diffusion_deploy/command/unified_command_interface.hpp"
#include "diffusion_deploy/guidance/whole_body_guidance.hpp"
#include "diffusion_deploy/obs/obs_terms.hpp"

#include <yaml-cpp/yaml.h>

#include <cstddef>
#include <fstream>
#include <string>
#include <vector>

namespace diffusion_deploy {

/** Selectable CSV column groups. Defaults preserve the original full schema. */
struct CsvRecordFields {
    bool metadata = true;
    bool command = true;
    bool condition = true;
    bool policy_obs = true;
    bool action = true;
    std::vector<std::string> robot_obs = {
        "body_pos", "body_rot", "body_lin_vel", "body_ang_vel",
        "root_pos", "root_rot", "joint_pos", "joint_vel",
        "projected_gravity", "base_lin_vel", "base_ang_vel",
        "last_actions",
    };
};

/** Recorder settings loaded primarily from the top-level FSM record_csv block. */
struct CsvRecordConfig {
    bool enabled = false;
    std::string path;
    CsvRecordFields fields;
};

/** Parse and validate a record_csv YAML mapping, inheriting omitted values. */
CsvRecordConfig parse_csv_record_config(
    const YAML::Node& node,
    const CsvRecordConfig& inherited = {});

/** Validate a fully resolved config (including path supplied by CLI). */
void validate_csv_record_config(const CsvRecordConfig& config);

/** Short human-readable list used by config validation and startup logging. */
std::string csv_record_fields_summary(const CsvRecordFields& fields);

class CsvRecorder {
public:
    /**
     * Open a new CSV file and write its complete, fixed-schema header.
     *
     * @param path              Output CSV path. Parent directories are created.
     * @param n_obs_steps       Number of history steps in policy_obs.
     * @param policy_obs_dim    Per-timestep composed observation dimension.
     * @param action_dim        Number of action values passed to env->step().
     * @param condition_dim     Number of command-condition values, or zero.
     * @param command_source    Metadata label such as joydev or cond_udp.
     */
    CsvRecorder(const std::string& path,
                int n_obs_steps,
                int policy_obs_dim,
                int action_dim,
                int condition_dim,
                std::string command_source,
                CsvRecordFields fields = {});
    ~CsvRecorder();

    CsvRecorder(const CsvRecorder&) = delete;
    CsvRecorder& operator=(const CsvRecorder&) = delete;

    /** Append one completed control-step record. */
    void append(int step,
                double time_s,
                bool policy_active,
                const std::string& fsm_state,
                const ObsTerms& robot_obs,
                const torch::Tensor& policy_obs,
                const torch::Tensor& action,
                const torch::Tensor& condition,
                const UnifiedCommandState* unified_command = nullptr,
                const WbgUdpFrame* wbg_udp_command = nullptr);

    /** Flush and close the file. Safe to call more than once. */
    void close();

    const std::string& path() const { return path_; }
    std::size_t row_count() const { return row_count_; }
    bool records_command() const { return fields_.command; }
    bool records_condition() const { return fields_.condition; }

private:
    std::string path_;
    std::string command_source_;
    int n_obs_steps_ = 0;
    int policy_obs_dim_ = 0;
    int action_dim_ = 0;
    int condition_dim_ = 0;
    CsvRecordFields fields_;
    std::ofstream output_;
    std::size_t row_count_ = 0;

    void write_header();
};

}  // namespace diffusion_deploy
