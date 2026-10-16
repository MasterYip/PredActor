/*
 * ===========================================================================
 *  joystick_parser.hpp  —  Standalone Linux joystick parser (header-only, C++17)
 * ===========================================================================
 *
 *  Drop this single file into any C++ project that needs to read joystick /
 *  gamepad input from ``/dev/input/js*`` on Linux.  Zero dependencies beyond
 *  the C++ standard library and the Linux kernel headers.
 *
 *  Author:  joystick_linux_fake (generated)
 *  License: MIT
 *  Version: 1.0.0
 *
 * ---------------------------------------------------------------------------
 *  Quick-Start
 * ---------------------------------------------------------------------------
 *
 *      #include "joystick_parser.hpp"
 *
 *      // 1. Pick a mapping — "xbox", "xbox_new", "ps5", or your own.
 *      const auto & mapping = joystick::get_mapping("xbox");
 *
 *      // 2. Open the device.
 *      joystick::JoystickParser parser("/dev/input/js0", &mapping);
 *      if (!parser.is_connected()) {
 *          std::cerr << "No gamepad found.\n";
 *          return 1;
 *      }
 *
 *      // 3. Poll inside your control / render loop (safe at >1 kHz).
 *      while (running) {
 *          parser.poll();   // drains all pending kernel events
 *
 *          float lx     = parser.get_axis_normalized("left_x");
 *          bool  a_btn  = parser.get_button("south");
 *
 *          // ... use the values ...
 *      }
 *
 *      // 4. Snapshot API (thread-safe, point-in-time copy).
 *      auto snap = parser.get_snapshot();
 *      std::cout << "left_x = " << snap.axes.at("left_x") << "\n";
 *
 * ---------------------------------------------------------------------------
 *  Built-in Mappings
 * ---------------------------------------------------------------------------
 *
 *  +---------+---------------------------+-------------------------------+
 *  | Name    | Logical axes               | Logical buttons               |
 *  +=========+===========================+===============================+
 *  | "xbox"  | left_x, left_y, l2,       | south, east, west, north,    |
 *  |         | right_x, right_y, r2,     | l1, r1, select, start, mode, |
 *  |         | dpad_x, dpad_y            | l3, r3                       |
 *  +---------+---------------------------+-------------------------------+
 *  |"xbox_new"| left/right sticks,        | south, east, raw buttons,    |
 *  |         | r2, l2, dpad_x, dpad_y   | west, north, select, l1, r1, |
 *  |         |                           | start, l3, r3                |
 *  +---------+---------------------------+-------------------------------+
 *  | "ps5"   | left_x, left_y, right_x,  | south, east, west, north,    |
 *  |         | l2, right_y, r2,          | l1, r1, l2_btn, r2_btn,      |
 *  |         | dpad_x, dpad_y            | select, start, mode, l3, r3, |
 *  |         |                           | touchpad, mic                |
 *  +---------+---------------------------+-------------------------------+
 *  |"beitong | left_x, left_y, right_x,  | south, east, share, west,    |
 *  | _kp20"  | right_y, r2, l2,          | north, turbo, l1, r1, mode,  |
 *  |         | dpad_x, dpad_y            | m1, select, start, m2, l3, r3|
 *  +---------+---------------------------+-------------------------------+
 *
 *  See the ``AxisMapping`` / ``ButtonMapping`` tables below for the exact
 *  physical-number → logical-name assignments.
 *
 * ---------------------------------------------------------------------------
 *  Shared Config Files
 * ---------------------------------------------------------------------------
 *
 *      auto mapping = joystick::load_mapping_file(
 *          "config/joystick_mappings/xbox_new.yaml");
 *
 *  Named presets automatically use files in ``config/joystick_mappings``
 *  when launched from the repository root. Set ``JOYSTICK_MAPPING_DIR`` to
 *  use that directory from another working directory. Compiled fallbacks keep
 *  the header standalone when the shared files are not installed.
 *
 *  Custom Mappings  (no config file required)
 * ---------------------------------------------------------------------------
 *
 *      joystick::JoystickMappingConfig my_map("MyController", 1);
 *      my_map.axes[0]  = joystick::AxisMapping{0, "left_x",  -32768, 32767};
 *      my_map.axes[1]  = joystick::AxisMapping{1, "left_y",  -32768, 32767};
 *      // ... add all axes & buttons ...
 *
 *      joystick::JoystickParser parser("/dev/input/js0", &my_map);
 *
 * ---------------------------------------------------------------------------
 *  Integrating With a Unitree Joystick
 * ---------------------------------------------------------------------------
 *
 *  This parser produces *logical* axis / button values.  To drive a
 *  ``unitree::common::UnitreeJoystick``, write a small adapter that calls
 *  the parser's accessors and then the Unitree object's ``operator()``
 *  methods.  See ``deploy/include/common/CustomJoystick.h`` for a worked
 *  example.
 *
 * ---------------------------------------------------------------------------
 *  Thread Safety
 * ---------------------------------------------------------------------------
 *
 *  - ``poll()``, ``get_axis_*()``, ``get_button()``, and ``get_snapshot()``
 *    are protected by an internal ``std::mutex`` and may be called from
 *    different threads.
 *  - The parser does **not** spawn a background thread — you are in control
 *    of when ``poll()`` runs.
 *
 * ---------------------------------------------------------------------------
 *  Requirements
 * ---------------------------------------------------------------------------
 *
 *  - Linux kernel with ``CONFIG_INPUT_JOYDEV``
 *  - C++17 or later
 *  - No external libraries (Boost, etc.)
 *
 * ===========================================================================
 */

#pragma once

#include <algorithm>
#include <array>
#include <cstring>
#include <cstdlib>
#include <fcntl.h>
#include <fstream>
#include <linux/joystick.h>
#include <mutex>
#include <stdexcept>
#include <string>
#include <unistd.h>
#include <utility>
#include <vector>

// ---------------------------------------------------------------------------
//  Namespace
// ---------------------------------------------------------------------------

namespace joystick {

// =========================================================================
//  Constants  (match Linux <linux/joystick.h>)
// =========================================================================

inline constexpr uint8_t JS_EVENT_BUTTON_MASK = 0x01;
inline constexpr uint8_t JS_EVENT_AXIS_MASK   = 0x02;
inline constexpr uint8_t JS_EVENT_INIT_MASK   = 0x80;

/// Maximum number of axes / buttons we track (generous upper bound).
inline constexpr int kMaxAxes   = 16;
inline constexpr int kMaxButtons = 32;

// =========================================================================
//  Mapping Data Types
// =========================================================================

/// Describes one physical axis (number, name, raw value range).
struct AxisMapping {
    int         number   = -1;   ///< Physical axis index (0-based)
    std::string logical;         ///< Logical name, e.g. "left_x", "l2", "dpad_x"
    int         min_val  = -32768;
    int         max_val  =  32767;
    std::string label;                ///< Display label, e.g. "Left Stick X"

    AxisMapping() = default;
    AxisMapping(int number_, std::string logical_, int min_val_ = -32768,
                int max_val_ = 32767, std::string label_ = {})
        : number(number_), logical(std::move(logical_)), min_val(min_val_),
          max_val(max_val_), label(std::move(label_)) {}
};

/// Describes one physical button (number, name).
struct ButtonMapping {
    int         number   = -1;   ///< Physical button index (0-based)
    std::string logical;         ///< Logical name, e.g. "south", "l1", "start"
    std::string label;           ///< Display label, e.g. "A", "LB", "Start"

    ButtonMapping() = default;
    ButtonMapping(int number_, std::string logical_, std::string label_ = {})
        : number(number_), logical(std::move(logical_)), label(std::move(label_)) {}
};

/// Complete joystick mapping  (physical number → logical name + metadata).
///
/// Create one from code or use the built-in ``xbox_mapping()`` /
/// ``ps5_mapping()`` factories.
struct JoystickMappingConfig {
    std::string name;
    int         version = 1;

    /// Physical axis number → AxisMapping.
    std::vector<AxisMapping>   axes;
    /// Physical button number → ButtonMapping.
    std::vector<ButtonMapping> buttons;

    JoystickMappingConfig() = default;
    JoystickMappingConfig(std::string name_, int ver_)
        : name(std::move(name_)), version(ver_) {}

    // -- Lookup helpers (O(n), but n ≤ 16) --------------------------------

    const AxisMapping* find_axis_by_number(int number) const {
        for (auto & a : axes)
            if (a.number == number) return &a;
        return nullptr;
    }
    const ButtonMapping* find_button_by_number(int number) const {
        for (auto & b : buttons)
            if (b.number == number) return &b;
        return nullptr;
    }
    const AxisMapping* find_axis_by_logical(const std::string & logical) const {
        for (auto & a : axes)
            if (a.logical == logical) return &a;
        return nullptr;
    }
    const ButtonMapping* find_button_by_logical(const std::string & logical) const {
        for (auto & b : buttons)
            if (b.logical == logical) return &b;
        return nullptr;
    }
};

inline bool is_trigger_axis(const std::string & logical) {
    return logical == "l2" || logical == "r2";
}

/** Normalize one Linux joydev axis using the declared physical range.
 *
 * Triggers are always exposed as pressure in [0,1], including drivers which
 * report the common signed joydev range (-32767 at rest, +32767 pressed).
 * An axis with no INIT/runtime event is treated as resting, rather than
 * interpreting the zero-initialized storage as a half-pressed signed trigger.
 */
inline float normalize_axis_value(int raw, const AxisMapping & am,
                                  bool initialized = true) {
    if (!initialized && is_trigger_axis(am.logical)) return 0.0f;
    const float r = static_cast<float>(raw);
    const float lo = static_cast<float>(am.min_val);
    const float hi = static_cast<float>(am.max_val);
    const float denom = hi - lo;
    if (denom <= 0.0f) return 0.0f;
    if (is_trigger_axis(am.logical) || am.min_val >= 0)
        return std::clamp((r - lo) / denom, 0.0f, 1.0f);
    return std::clamp(2.0f * (r - lo) / denom - 1.0f, -1.0f, 1.0f);
}

// =========================================================================
//  Shared YAML Mapping Files
// =========================================================================

inline std::string trim_mapping_value(const std::string & value) {
    const auto first = value.find_first_not_of(" \t\r\n");
    if (first == std::string::npos) return {};
    const auto last = value.find_last_not_of(" \t\r\n");
    return value.substr(first, last - first + 1);
}

inline std::string parse_yaml_scalar(const std::string & value) {
    std::string scalar = trim_mapping_value(value);
    if (scalar.size() >= 2 &&
        ((scalar.front() == '"' && scalar.back() == '"') ||
         (scalar.front() == '\'' && scalar.back() == '\'')))
        return scalar.substr(1, scalar.size() - 2);
    return scalar;
}

/// Load the nested YAML schema used in config/joystick_mappings.
/// This intentionally parses the project mapping schema, not arbitrary YAML.
inline JoystickMappingConfig load_mapping_file(const std::string & path) {
    std::ifstream input(path);
    if (!input)
        throw std::runtime_error("Cannot open joystick mapping: " + path);

    JoystickMappingConfig config;
    std::string section;
    std::string line;
    AxisMapping * current_axis = nullptr;
    ButtonMapping * current_button = nullptr;
    int line_number = 0;
    while (std::getline(input, line)) {
        ++line_number;
        const auto first = line.find_first_not_of(' ');
        if (first == std::string::npos || line[first] == '#') continue;
        if (line.find('\t') != std::string::npos)
            throw std::runtime_error("Invalid joystick mapping " + path + ":" +
                                     std::to_string(line_number) +
                                     " (tabs are not supported)");
        const std::size_t indent = first;
        line = trim_mapping_value(line);

        const auto colon = line.find(':');
        if (colon == std::string::npos)
            throw std::runtime_error(
                "Invalid joystick mapping " + path + ":" +
                std::to_string(line_number) + " (expected key: value)");
        const std::string key = trim_mapping_value(line.substr(0, colon));
        const std::string value = parse_yaml_scalar(line.substr(colon + 1));

        try {
            if (indent == 0) {
                current_axis = nullptr;
                current_button = nullptr;
                if ((key == "axes" || key == "buttons") && value.empty()) {
                    section = key;
                } else if (key == "name") {
                    config.name = value;
                } else if (key == "version") {
                    config.version = std::stoi(value);
                }
            } else if (indent == 2 && value.empty()) {
                if (section == "axes") {
                    config.axes.emplace_back(std::stoi(key), "");
                    current_axis = &config.axes.back();
                    current_button = nullptr;
                } else if (section == "buttons") {
                    config.buttons.emplace_back(std::stoi(key), "");
                    current_button = &config.buttons.back();
                    current_axis = nullptr;
                } else {
                    throw std::runtime_error("entry outside axes or buttons");
                }
            } else if (indent == 4 && current_axis) {
                if (key == "logical") current_axis->logical = value;
                else if (key == "label") current_axis->label = value;
                else if (key == "min") current_axis->min_val = std::stoi(value);
                else if (key == "max") current_axis->max_val = std::stoi(value);
            } else if (indent == 4 && current_button) {
                if (key == "logical") current_button->logical = value;
                else if (key == "label") current_button->label = value;
            } else {
                throw std::runtime_error("unexpected indentation or mapping field");
            }
        } catch (const std::exception & error) {
            throw std::runtime_error(
                "Invalid joystick mapping " + path + ":" +
                std::to_string(line_number) + " (" + error.what() + ")");
        }
    }
    if (config.name.empty())
        throw std::runtime_error("Invalid joystick mapping " + path +
                                 " (missing controller name)");
    for (const auto & axis : config.axes)
        if (axis.logical.empty())
            throw std::runtime_error("Invalid joystick mapping " + path +
                                     " (axis missing logical name)");
    for (const auto & button : config.buttons)
        if (button.logical.empty())
            throw std::runtime_error("Invalid joystick mapping " + path +
                                     " (button missing logical name)");
    return config;
}

inline JoystickMappingConfig load_shared_preset_or(
    const std::string & identifier, JoystickMappingConfig fallback) {
    std::vector<std::string> paths;
    if (const char * directory = std::getenv("JOYSTICK_MAPPING_DIR"))
        paths.emplace_back(std::string(directory) + "/" + identifier + ".yaml");
    paths.emplace_back("config/joystick_mappings/" + identifier + ".yaml");
    for (const auto & path : paths) {
        std::ifstream candidate(path);
        if (candidate.good()) return load_mapping_file(path);
    }
    return fallback;
}

// =========================================================================
//  Built-in Mappings
// =========================================================================

/// Xbox 360 / One / Series mapping.
inline const JoystickMappingConfig& xbox_mapping() {
    static const JoystickMappingConfig m = [] {
        JoystickMappingConfig c("Xbox 360 / One / Series", 1);
        c.axes = {
            {0, "left_x",  -32768, 32767},
            {1, "left_y",  -32768, 32767},
            {2, "l2",      -32767, 32767},
            {3, "right_x", -32768, 32767},
            {4, "right_y", -32768, 32767},
            {5, "r2",      -32767, 32767},
            {6, "dpad_x",      -1,     1},
            {7, "dpad_y",      -1,     1},
        };
        c.buttons = {
            {0,  "south"},
            {1,  "east"},
            {2,  "west"},
            {3,  "north"},
            {4,  "l1"},
            {5,  "r1"},
            {6,  "select"},
            {7,  "start"},
            {8,  "mode"},
            {9,  "l3"},
            {10, "r3"},
        };
        return load_shared_preset_or("xbox", std::move(c));
    }();
    return m;
}

/// Xbox One / Series mapping after the BLE firmware update.
inline const JoystickMappingConfig& xbox_new_mapping() {
    static const JoystickMappingConfig m = [] {
        JoystickMappingConfig c("Xbox One / Series (updated BLE firmware)", 1);
        c.axes = {
            {0, "left_x",  -32768, 32767},
            {1, "left_y",  -32768, 32767},
            {2, "right_x", -32768, 32767},
            {3, "right_y", -32768, 32767},
            {4, "r2",      -32767, 32767},
            {5, "l2",      -32767, 32767},
            {6, "dpad_x",      -1,     1},
            {7, "dpad_y",      -1,     1},
        };
        c.buttons = {
            {0, "south"}, {1, "east"}, {2, "button_13"}, {3, "west"},
            {4, "north"}, {5, "select"}, {6, "l1"}, {7, "r1"},
            {8, "button_14"}, {9, "start"}, {10, "button_10"},
            {11, "button_11"}, {13, "l3"}, {14, "r3"},
        };
        return load_shared_preset_or("xbox_new", std::move(c));
    }();
    return m;
}

/// Beitong Kunpeng 20 (北通鲲鹏20) — KP20-specific layout.
inline const JoystickMappingConfig& beitong_kp20_mapping() {
    static const JoystickMappingConfig m = [] {
        JoystickMappingConfig c("Beitong Kunpeng 20 (北通鲲鹏20)", 1);
        c.axes = {
            {0, "left_x",  -32768, 32767},
            {1, "left_y",  -32768, 32767},
            {2, "right_x", -32768, 32767},
            {3, "right_y", -32768, 32767},
            {4, "r2",      -32767, 32767},
            {5, "l2",      -32767, 32767},
            {6, "dpad_x",      -1,     1},
            {7, "dpad_y",      -1,     1},
        };
        c.buttons = {
            {0,  "south"},
            {1,  "east"},
            {2,  "share"},
            {3,  "west"},
            {4,  "north"},
            {5,  "turbo"},
            {6,  "l1"},
            {7,  "r1"},
            {8,  "mode"},
            {9,  "m1"},
            {10, "select"},
            {11, "start"},
            {12, "m2"},
            {13, "l3"},
            {14, "r3"},
        };
        return load_shared_preset_or("beitong_kp20", std::move(c));
    }();
    return m;
}

/// PS5 DualSense (hid-playstation) mapping.
inline const JoystickMappingConfig& ps5_mapping() {
    static const JoystickMappingConfig m = [] {
        JoystickMappingConfig c("PS5 DualSense (hid-playstation)", 1);
        c.axes = {
            {0, "left_x",  -32768, 32767},
            {1, "left_y",  -32768, 32767},
            {2, "right_x", -32768, 32767},
            {3, "l2",      -32767, 32767},
            {4, "right_y", -32768, 32767},
            {5, "r2",      -32767, 32767},
            {6, "dpad_x",      -1,     1},
            {7, "dpad_y",      -1,     1},
        };
        c.buttons = {
            {0,  "south"},
            {1,  "east"},
            {2,  "west"},
            {3,  "north"},
            {4,  "l1"},
            {5,  "r1"},
            {6,  "l2_btn"},
            {7,  "r2_btn"},
            {8,  "select"},
            {9,  "start"},
            {10, "mode"},
            {11, "l3"},
            {12, "r3"},
            {13, "touchpad"},
            {14, "mic"},
        };
        return load_shared_preset_or("ps5", std::move(c));
    }();
    return m;
}

/// Resolve a mapping identifier.
///
/// Named presets use the shared YAML file when available, then fall back to
/// the compiled mapping. Use load_mapping_file() for an explicit file path.
///
/// Returns a reference to a static, never-dangling mapping.
/// Throws ``std::runtime_error`` on unknown identifiers.
inline const JoystickMappingConfig& get_mapping(const std::string & identifier) {
    if (identifier == "xbox" || identifier == "xbox360" || identifier == "xboxone")
        return xbox_mapping();
    if (identifier == "xbox_new" || identifier == "xbox_ble")
        return xbox_new_mapping();
    if (identifier == "ps5" || identifier == "ps" || identifier == "playstation")
        return ps5_mapping();
    if (identifier == "beitong_kp20")
        return beitong_kp20_mapping();

    throw std::runtime_error(
        "joystick::get_mapping: unknown mapping '" + identifier + "'.  "
        "Built-in choices: \"xbox\", \"xbox_new\", \"ps5\", "
        "\"beitong_kp20\"; use load_mapping_file() for a YAML path.");
}

// =========================================================================
//  Event & Snapshot Types
// =========================================================================

/// A single parsed joystick event with optional logical names.
struct JoystickEvent {
    uint32_t    timestamp_ms = 0;
    uint8_t     type         = 0;    ///< JS_EVENT_BUTTON_MASK or JS_EVENT_AXIS_MASK
    uint8_t     number       = 0;    ///< Physical axis / button index
    int16_t     value        = 0;    ///< Raw value
    std::string logical;             ///< Logical name (empty if no mapping)
    bool        is_init      = false;///< True for synthetic kernel INIT events
};

/// Thread-safe point-in-time copy of the parser state.
struct JoystickSnapshot {
    /// Logical axis name → raw value  (e.g. "left_x" → 1234)
    std::vector<std::pair<std::string, int>> axes;
    /// Logical button name → pressed   (e.g. "south" → true)
    std::vector<std::pair<std::string, bool>> buttons;
};

// =========================================================================
//  JoystickParser
// =========================================================================

/// Reads raw ``/dev/input/js*`` events from a Linux joystick device.
///
/// Usage summary::
///
///     joystick::JoystickParser p("/dev/input/js0",
///                                 &joystick::get_mapping("xbox"));
///     while (running) {
///         p.poll();
///         float lx = p.get_axis_normalized("left_x");
///         bool  a  = p.get_button("south");
///     }
///
/// The parser does **not** spawn a background thread — call ``poll()`` from
/// your own control loop (it is non-blocking and safe at >1 kHz).
///
/// All public methods are thread-safe  (protected by an internal mutex).
class JoystickParser {
public:
    // -- construction / destruction ----------------------------------------

    /// Open *device_path* (e.g. ``"/dev/input/js0"``) with non-blocking I/O.
    ///
    /// If *mapping* is ``nullptr``, logical-name accessors will return
    /// zero / false.  Physical-number accessors still work.
    explicit JoystickParser(const std::string & device_path,
                            const JoystickMappingConfig * mapping = nullptr)
        : mapping_(mapping)
    {
        fd_ = ::open(device_path.c_str(), O_RDONLY | O_NONBLOCK);
        if (fd_ >= 0) {
            drain_init_events();
        }
    }

    ~JoystickParser() {
        if (fd_ >= 0) {
            ::close(fd_);
            fd_ = -1;
        }
    }

    // Non-copyable, movable.
    JoystickParser(const JoystickParser &) = delete;
    JoystickParser & operator=(const JoystickParser &) = delete;
    JoystickParser(JoystickParser && other) noexcept
        : fd_(other.fd_), mapping_(other.mapping_) {
        other.fd_ = -1;
        std::lock_guard<std::mutex> lk(other.mutex_);
        axes_    = other.axes_;
        axis_initialized_ = other.axis_initialized_;
        buttons_ = other.buttons_;
    }
    JoystickParser & operator=(JoystickParser &&) = delete;

    // -- query -------------------------------------------------------------

    bool is_connected() const { return fd_ >= 0; }

    /// Return the mapping in use (may be ``nullptr``).
    const JoystickMappingConfig * mapping() const { return mapping_; }
    void set_mapping(const JoystickMappingConfig * m) { mapping_ = m; }

    // -- poll --------------------------------------------------------------

    /// Drain all pending kernel events into the internal state.
    ///
    /// Non-blocking — returns immediately if no events are available.
    /// Call this once per control-loop iteration (safe at >1 kHz).
    void poll() {
        if (fd_ < 0) return;

        struct js_event ev;
        ssize_t n;
        std::lock_guard<std::mutex> lk(mutex_);
        while ((n = ::read(fd_, &ev, sizeof(ev))) == static_cast<ssize_t>(sizeof(ev))) {
            const uint8_t base = ev.type & ~JS_EVENT_INIT_MASK;
            if (base == JS_EVENT_AXIS_MASK) {
                if (ev.number < kMaxAxes) {
                    axes_[ev.number] = ev.value;
                    axis_initialized_[ev.number] = true;
                }
            } else if (base == JS_EVENT_BUTTON_MASK) {
                if (ev.number < kMaxButtons) {
                    buttons_[ev.number] = ev.value;
                }
            }
        }
    }

    // -- axis access (by logical name) -------------------------------------

    /// Raw axis value by logical name, e.g. ``get_axis_raw("left_x")``.
    /// Returns 0 if the name is unknown or no mapping is set.
    int get_axis_raw(const std::string & logical) const {
        std::lock_guard<std::mutex> lk(mutex_);
        if (mapping_) {
            if (auto * am = mapping_->find_axis_by_logical(logical))
                return axes_[am->number];
        }
        return 0;
    }

    /// Normalised axis value by logical name.
    ///
    /// Uses the mapping's *min_val* / *max_val* to produce:
    /// - ``[-1.0, 1.0]`` for bidirectional axes (min < 0), e.g. sticks
    /// - ``[ 0.0, 1.0]`` for unidirectional axes (min ≥ 0), e.g. triggers
    ///
    /// Returns 0 if the logical name is unknown or no mapping is set.
    float get_axis_normalized(const std::string & logical) const {
        std::lock_guard<std::mutex> lk(mutex_);
        if (mapping_) {
            if (auto * am = mapping_->find_axis_by_logical(logical)) {
                return normalize_axis_value(
                    axes_[am->number], *am, axis_initialized_[am->number]);
            }
        }
        return 0.0f;
    }

    // -- axis access (by physical number — no mapping needed) --------------

    int get_axis_raw_by_number(int number) const {
        if (number < 0 || number >= kMaxAxes) return 0;
        std::lock_guard<std::mutex> lk(mutex_);
        return axes_[number];
    }

    // -- button access -----------------------------------------------------

    /// Button state by logical name, e.g. ``get_button("south")``.
    /// Returns ``false`` if the name is unknown or no mapping is set.
    bool get_button(const std::string & logical) const {
        std::lock_guard<std::mutex> lk(mutex_);
        if (mapping_) {
            if (auto * bm = mapping_->find_button_by_logical(logical))
                return buttons_[bm->number] != 0;
        }
        return false;
    }

    /// Button state by physical number (no mapping needed).
    bool get_button_by_number(int number) const {
        if (number < 0 || number >= kMaxButtons) return false;
        std::lock_guard<std::mutex> lk(mutex_);
        return buttons_[number] != 0;
    }

    // -- snapshot ----------------------------------------------------------

    /// Return a point-in-time copy of the full axis & button state.
    ///
    /// Axes values use logical names when a mapping is set, otherwise
    /// ``"axis_N"`` fallback strings.  Buttons similarly use logical names
    /// or ``"button_N"``.
    JoystickSnapshot get_snapshot() const {
        std::lock_guard<std::mutex> lk(mutex_);
        JoystickSnapshot snap;

        if (mapping_) {
            for (auto & am : mapping_->axes) {
                snap.axes.emplace_back(am.logical, axes_[am.number]);
            }
            for (auto & bm : mapping_->buttons) {
                snap.buttons.emplace_back(bm.logical, buttons_[bm.number] != 0);
            }
        } else {
            for (int i = 0; i < kMaxAxes; ++i) {
                if (axes_[i] != 0)
                    snap.axes.emplace_back("axis_" + std::to_string(i), axes_[i]);
            }
            for (int i = 0; i < kMaxButtons; ++i) {
                if (buttons_[i] != 0)
                    snap.buttons.emplace_back("button_" + std::to_string(i), buttons_[i] != 0);
            }
        }
        return snap;
    }

    // -- static helpers ----------------------------------------------------

    /// Return sorted list of ``/dev/input/js*`` device paths found on the system.
    static std::vector<std::string> list_devices() {
        std::vector<std::string> out;
        for (int i = 0; i < 32; ++i) {
            std::string path = "/dev/input/js" + std::to_string(i);
            if (::access(path.c_str(), R_OK) == 0)
                out.push_back(path);
        }
        return out;
    }

    /// Return the first available js device path.
    ///
    /// Throws ``std::runtime_error`` if no device is found.
    static std::string default_device() {
        auto devs = list_devices();
        if (devs.empty())
            throw std::runtime_error("No joystick device found under /dev/input/js*");
        return devs.front();
    }

private:
    // -- helpers -----------------------------------------------------------

    /// Drain synthetic INIT events that the kernel emits on open().
    /// Called once from the constructor while we still own the fd exclusively.
    void drain_init_events() {
        // The fd is already O_NONBLOCK.  Kernel INIT events are flushed
        // synchronously inside open(), so they are available immediately.
        // We drain them with non-blocking reads — no need to switch to
        // blocking mode (which would hang after the last INIT event).
        struct js_event ev;
        for (int attempt = 0; attempt < kMaxAxes + kMaxButtons; ++attempt) {
            ssize_t n = ::read(fd_, &ev, sizeof(ev));
            if (n != static_cast<ssize_t>(sizeof(ev))) break; // EAGAIN or EOF

            const uint8_t base = ev.type & ~JS_EVENT_INIT_MASK;
            if (base == JS_EVENT_AXIS_MASK && ev.number < kMaxAxes) {
                axes_[ev.number] = ev.value;
                axis_initialized_[ev.number] = true;
            } else if (base == JS_EVENT_BUTTON_MASK && ev.number < kMaxButtons) {
                buttons_[ev.number] = ev.value;
            }
        }
    }

    // -- data --------------------------------------------------------------

    int fd_ = -1;
    const JoystickMappingConfig * mapping_ = nullptr;

    std::array<int, kMaxAxes>    axes_{};
    std::array<bool, kMaxAxes>   axis_initialized_{};
    std::array<int, kMaxButtons> buttons_{};

    mutable std::mutex mutex_;
};

} // namespace joystick
