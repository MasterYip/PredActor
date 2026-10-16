#include "diffusion_deploy/runner/csv_recorder.hpp"

#include <array>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <set>
#include <sstream>
#include <stdexcept>

namespace diffusion_deploy {
namespace {

struct TensorSpec {
    const char* name;
    int size;
};

// Keep the raw observation schema stable so recordings from different runs
// can be loaded by the same analysis script.  UnitreeEnv supplies all terms;
// undefined terms are represented by empty CSV cells for test/fake envs.
constexpr std::array<TensorSpec, 12> kRobotObsSpecs{{
    {"body_pos", 30 * 3},
    {"body_rot", 30 * 4},
    {"body_lin_vel", 30 * 3},
    {"body_ang_vel", 30 * 3},
    {"root_pos", 3},
    {"root_rot", 4},
    {"joint_pos", 29},
    {"joint_vel", 29},
    {"projected_gravity", 3},
    {"base_lin_vel", 3},
    {"base_ang_vel", 3},
    {"last_actions", 29},
}};

std::size_t robot_obs_index(const std::string& name) {
    for (std::size_t i = 0; i < kRobotObsSpecs.size(); ++i) {
        if (name == kRobotObsSpecs[i].name) return i;
    }
    throw std::invalid_argument(
        "record_csv.fields.robot_obs: unknown field '" + name + "'");
}

void require_mapping(const YAML::Node& node, const std::string& name) {
    if (!node.IsMap())
        throw std::invalid_argument(name + " must be a YAML mapping");
}

void require_known_keys(const YAML::Node& node,
                        const std::set<std::string>& allowed,
                        const std::string& name) {
    for (auto it = node.begin(); it != node.end(); ++it) {
        const auto key = it->first.as<std::string>();
        if (allowed.count(key) == 0)
            throw std::invalid_argument(name + ": unknown key '" + key + "'");
    }
}

void delimiter(std::ostringstream& row, bool& first) {
    if (!first) row << ',';
    first = false;
}

template <typename T>
void number(std::ostringstream& row, bool& first, T value) {
    delimiter(row, first);
    row << std::setprecision(17) << value;
}

void empty(std::ostringstream& row, bool& first) {
    delimiter(row, first);
}

void boolean(std::ostringstream& row, bool& first, bool value) {
    number(row, first, value ? 1 : 0);
}

void string_cell(std::ostringstream& row, bool& first, const std::string& value) {
    delimiter(row, first);
    row << '"';
    for (const char c : value) {
        if (c == '"') row << "\"\"";
        else row << c;
    }
    row << '"';
}

void header_cell(std::ostringstream& header, bool& first, const std::string& value) {
    if (!first) header << ',';
    first = false;
    header << value;
}

void add_indexed_header(std::ostringstream& header,
                        bool& first,
                        const std::string& prefix,
                        int count) {
    for (int i = 0; i < count; ++i) {
        std::ostringstream name;
        name << prefix << std::setw(3) << std::setfill('0') << i;
        header_cell(header, first, name.str());
    }
}

void tensor_values(std::ostringstream& row,
                   bool& first,
                   const torch::Tensor& tensor,
                   int expected,
                   const std::string& name) {
    if (!tensor.defined()) {
        for (int i = 0; i < expected; ++i) empty(row, first);
        return;
    }
    const auto flat = tensor.detach().to(torch::kCPU, torch::kFloat64)
                          .contiguous().flatten();
    if (flat.numel() != expected) {
        throw std::runtime_error(
            "CsvRecorder: " + name + " has " +
            std::to_string(flat.numel()) + " values; expected " +
            std::to_string(expected));
    }
    const auto* values = flat.data_ptr<double>();
    for (int i = 0; i < expected; ++i) number(row, first, values[i]);
}

void vector_values(std::ostringstream& row,
                   bool& first,
                   const std::vector<float>& values,
                   int expected,
                   const std::string& name) {
    if (values.empty()) {
        for (int i = 0; i < expected; ++i) empty(row, first);
        return;
    }
    if (static_cast<int>(values.size()) != expected) {
        throw std::runtime_error(
            "CsvRecorder: " + name + " has " +
            std::to_string(values.size()) + " values; expected " +
            std::to_string(expected));
    }
    for (const float value : values) number(row, first, value);
}

}  // namespace

CsvRecordConfig parse_csv_record_config(
    const YAML::Node& node,
    const CsvRecordConfig& inherited) {
    if (!node || node.IsNull()) return inherited;
    require_mapping(node, "record_csv");
    require_known_keys(node, {"enabled", "path", "fields"}, "record_csv");

    CsvRecordConfig config = inherited;
    if (node["enabled"]) config.enabled = node["enabled"].as<bool>();
    if (node["path"]) {
        config.path = node["path"].as<std::string>();
        if (!node["enabled"]) config.enabled = !config.path.empty();
    }

    const auto fields = node["fields"];
    if (fields) {
        require_mapping(fields, "record_csv.fields");
        require_known_keys(
            fields,
            {"metadata", "command", "condition", "policy_obs",
             "robot_obs", "action"},
            "record_csv.fields");
        if (fields["metadata"])
            config.fields.metadata = fields["metadata"].as<bool>();
        if (fields["command"])
            config.fields.command = fields["command"].as<bool>();
        if (fields["condition"])
            config.fields.condition = fields["condition"].as<bool>();
        if (fields["policy_obs"])
            config.fields.policy_obs = fields["policy_obs"].as<bool>();
        if (fields["action"])
            config.fields.action = fields["action"].as<bool>();
        if (fields["robot_obs"]) {
            const auto selected = fields["robot_obs"];
            if (!selected.IsSequence())
                throw std::invalid_argument(
                    "record_csv.fields.robot_obs must be a YAML sequence");
            config.fields.robot_obs.clear();
            std::set<std::string> seen;
            for (const auto& item : selected) {
                const auto name = item.as<std::string>();
                robot_obs_index(name);
                if (!seen.insert(name).second)
                    throw std::invalid_argument(
                        "record_csv.fields.robot_obs: duplicate field '" +
                        name + "'");
                config.fields.robot_obs.push_back(name);
            }
        }
    }
    auto selection_only = config;
    selection_only.enabled = false;
    validate_csv_record_config(selection_only);
    return config;
}

void validate_csv_record_config(const CsvRecordConfig& config) {
    std::set<std::string> seen;
    for (const auto& name : config.fields.robot_obs) {
        robot_obs_index(name);
        if (!seen.insert(name).second)
            throw std::invalid_argument(
                "record_csv.fields.robot_obs: duplicate field '" + name + "'");
    }
    if (!config.enabled) return;
    if (config.path.empty())
        throw std::invalid_argument(
            "record_csv.enabled is true but record_csv.path is empty");
    if (!config.fields.metadata && !config.fields.command
        && !config.fields.condition && !config.fields.policy_obs
        && config.fields.robot_obs.empty() && !config.fields.action)
        throw std::invalid_argument("record_csv.fields selects no CSV columns");
}

std::string csv_record_fields_summary(const CsvRecordFields& fields) {
    std::ostringstream out;
    bool first = true;
    auto add = [&](const std::string& value) {
        if (!first) out << ',';
        first = false;
        out << value;
    };
    if (fields.metadata) add("metadata");
    if (fields.command) add("command");
    if (fields.condition) add("condition");
    if (fields.policy_obs) add("policy_obs");
    if (!fields.robot_obs.empty()) {
        std::ostringstream robot;
        robot << "robot_obs[";
        for (std::size_t i = 0; i < fields.robot_obs.size(); ++i) {
            if (i > 0) robot << '|';
            robot << fields.robot_obs[i];
        }
        robot << ']';
        add(robot.str());
    }
    if (fields.action) add("action");
    return out.str();
}

CsvRecorder::CsvRecorder(const std::string& path,
                         int n_obs_steps,
                         int policy_obs_dim,
                         int action_dim,
                         int condition_dim,
                         std::string command_source,
                         CsvRecordFields fields)
    : path_(path),
      command_source_(std::move(command_source)),
      n_obs_steps_(n_obs_steps),
      policy_obs_dim_(policy_obs_dim),
      action_dim_(action_dim),
      condition_dim_(condition_dim),
      fields_(std::move(fields)) {
    if (path_.empty()) throw std::invalid_argument("CsvRecorder: output path is empty");
    if (n_obs_steps_ <= 0 || policy_obs_dim_ <= 0 || action_dim_ <= 0
        || condition_dim_ < 0) {
        throw std::invalid_argument("CsvRecorder: invalid recording dimensions");
    }
    validate_csv_record_config({true, path_, fields_});

    const std::filesystem::path output_path(path_);
    const auto parent = output_path.parent_path();
    if (!parent.empty()) {
        std::error_code ec;
        std::filesystem::create_directories(parent, ec);
        if (ec) {
            throw std::runtime_error(
                "CsvRecorder: cannot create parent directory '" +
                parent.string() + "': " + ec.message());
        }
    }
    output_.open(output_path, std::ios::out | std::ios::trunc);
    if (!output_) {
        throw std::runtime_error("CsvRecorder: cannot open output: " + path_);
    }
    write_header();
}

CsvRecorder::~CsvRecorder() {
    try {
        close();
    } catch (const std::exception& e) {
        std::cerr << "[CsvRecorder] close failed: " << e.what() << "\n";
    }
}

void CsvRecorder::write_header() {
    std::ostringstream header;
    bool first = true;
    if (fields_.metadata) {
        for (const char* name : {
                 "step", "time_s", "command_source", "fsm_state",
                 "policy_active"})
            header_cell(header, first, name);
    }
    if (fields_.command) {
        for (const char* name : {
                 "command_sequence", "command_monotonic_ms",
                 "command_joystick_connected", "command_motion",
                 "command_motion_hash", "command_wbg_vx_enabled",
                 "command_wbg_vx", "command_wbg_vx_kp",
                 "command_wbg_vy_enabled", "command_wbg_vy",
                 "command_wbg_vy_kp", "command_wbg_wz_enabled",
                 "command_wbg_wz", "command_wbg_wz_kp"})
            header_cell(header, first, name);
    }
    if (fields_.condition)
        add_indexed_header(header, first, "command_condition_", condition_dim_);
    if (fields_.policy_obs)
        add_indexed_header(header, first, "policy_obs_",
                           n_obs_steps_ * policy_obs_dim_);
    for (const auto& name : fields_.robot_obs) {
        const auto& spec = kRobotObsSpecs[robot_obs_index(name)];
        add_indexed_header(header, first,
                           std::string("robot_obs_") + spec.name + "_", spec.size);
    }
    if (fields_.action)
        add_indexed_header(header, first, "action_", action_dim_);
    output_ << header.str() << '\n';
    if (!output_) throw std::runtime_error("CsvRecorder: failed to write CSV header");
}

void CsvRecorder::append(int step,
                         double time_s,
                         bool policy_active,
                         const std::string& fsm_state,
                         const ObsTerms& robot_obs,
                         const torch::Tensor& policy_obs,
                         const torch::Tensor& action,
                         const torch::Tensor& condition,
                         const UnifiedCommandState* unified_command,
                         const WbgUdpFrame* wbg_udp_command) {
    if (!output_.is_open()) throw std::runtime_error("CsvRecorder: append after close");

    std::ostringstream row;
    bool first = true;
    if (fields_.metadata) {
        number(row, first, step);
        number(row, first, time_s);
        string_cell(row, first, command_source_);
        string_cell(row, first, fsm_state);
        boolean(row, first, policy_active);
    }

    if (fields_.command) {
        if (unified_command) {
            number(row, first, unified_command->sequence);
            number(row, first, unified_command->monotonic_ms);
            boolean(row, first, unified_command->joystick_connected);
            string_cell(row, first, unified_command->motion_name);
            string_cell(row, first, unified_command->motion_hash);
            boolean(row, first, unified_command->wbg.enabled
                && unified_command->wbg.linear_enabled);
            number(row, first, unified_command->wbg.vx);
            number(row, first, unified_command->wbg.kp);
            boolean(row, first, unified_command->wbg.enabled
                && unified_command->wbg.linear_enabled);
            number(row, first, unified_command->wbg.vy);
            number(row, first, unified_command->wbg.kp);
            boolean(row, first, unified_command->wbg.enabled
                && unified_command->wbg.yaw_enabled);
            number(row, first, unified_command->wbg.wz);
            number(row, first, unified_command->wbg.kp);
        } else {
            for (int i = 0; i < 5; ++i) empty(row, first);
            if (wbg_udp_command) {
                number(row, first, wbg_udp_command->vx_enabled);
                number(row, first, wbg_udp_command->vx_command);
                number(row, first, wbg_udp_command->vx_kp);
                number(row, first, wbg_udp_command->vy_enabled);
                number(row, first, wbg_udp_command->vy_command);
                number(row, first, wbg_udp_command->vy_kp);
                number(row, first, wbg_udp_command->wz_enabled);
                number(row, first, wbg_udp_command->wz_command);
                number(row, first, wbg_udp_command->wz_kp);
            } else {
                for (int i = 0; i < 9; ++i) empty(row, first);
            }
        }
    }

    if (fields_.condition) {
        if (condition.defined()) {
            tensor_values(row, first, condition, condition_dim_, "condition");
        } else if (unified_command) {
            vector_values(row, first, unified_command->latent, condition_dim_,
                          "unified command latent");
        } else {
            for (int i = 0; i < condition_dim_; ++i) empty(row, first);
        }
    }

    if (fields_.policy_obs)
        tensor_values(row, first, policy_obs, n_obs_steps_ * policy_obs_dim_,
                      "policy observation");

    const std::array<const torch::Tensor*, 12> robot_tensors{{
        &robot_obs.body_pos,
        &robot_obs.body_rot,
        &robot_obs.body_lin_vel,
        &robot_obs.body_ang_vel,
        &robot_obs.root_pos,
        &robot_obs.root_rot,
        &robot_obs.joint_pos,
        &robot_obs.joint_vel,
        &robot_obs.projected_gravity,
        &robot_obs.base_lin_vel,
        &robot_obs.base_ang_vel,
        &robot_obs.last_actions,
    }};
    for (const auto& name : fields_.robot_obs) {
        const auto index = robot_obs_index(name);
        tensor_values(row, first, *robot_tensors[index],
                      kRobotObsSpecs[index].size,
                      std::string("robot observation ") + name);
    }
    if (fields_.action)
        tensor_values(row, first, action, action_dim_, "action");

    output_ << row.str() << '\n';
    if (!output_) throw std::runtime_error("CsvRecorder: failed while writing row");
    ++row_count_;
}

void CsvRecorder::close() {
    if (!output_.is_open()) return;
    output_.flush();
    if (!output_) throw std::runtime_error("CsvRecorder: flush failed for " + path_);
    output_.close();
}

}  // namespace diffusion_deploy
