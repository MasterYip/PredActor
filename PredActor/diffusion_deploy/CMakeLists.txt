cmake_minimum_required(VERSION 3.16)
project(diffusion_deploy CXX)

include(GNUInstallDirs)
option(BUILD_TESTING "Build deployment tests" OFF)
if(BUILD_TESTING)
    include(CTest)
endif()

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_BUILD_RPATH_USE_ORIGIN ON)
set(CMAKE_INSTALL_RPATH "$ORIGIN;$ORIGIN/../${CMAKE_INSTALL_LIBDIR}")
set(CMAKE_INSTALL_RPATH_USE_LINK_PATH OFF)

set(DEPLOY_PROFILE "" CACHE STRING "Locked deployment profile")
set(DEPLOY_LOCK_FILE "${CMAKE_CURRENT_SOURCE_DIR}/deps/platform-lock.json"
    CACHE FILEPATH "Deployment platform lock")
if(DEPLOY_PROFILE)
    find_package(Python3 3.8 COMPONENTS Interpreter REQUIRED)
    set(_profile_cmake "${CMAKE_BINARY_DIR}/deploy-profile.cmake")
    execute_process(
        COMMAND "${Python3_EXECUTABLE}"
                "${CMAKE_CURRENT_SOURCE_DIR}/tools/read_platform_lock.py"
                --lock "${DEPLOY_LOCK_FILE}"
                --profile "${DEPLOY_PROFILE}"
                --output "${_profile_cmake}"
        RESULT_VARIABLE _profile_result
        ERROR_VARIABLE _profile_error)
    if(NOT _profile_result EQUAL 0)
        message(FATAL_ERROR "Platform lock validation failed: ${_profile_error}")
    endif()
    include("${_profile_cmake}")
    if(DIFFUSION_DEPLOY_EXPECTED_ARCH STREQUAL "x86_64")
        if(NOT CMAKE_SYSTEM_PROCESSOR MATCHES "^(x86_64|amd64|AMD64)$")
            message(FATAL_ERROR "Profile architecture mismatch: ${CMAKE_SYSTEM_PROCESSOR}")
        endif()
    elseif(DIFFUSION_DEPLOY_EXPECTED_ARCH STREQUAL "aarch64")
        if(NOT CMAKE_SYSTEM_PROCESSOR MATCHES "^(aarch64|arm64)$")
            message(FATAL_ERROR "Profile architecture mismatch: ${CMAKE_SYSTEM_PROCESSOR}")
        endif()
    else()
        message(FATAL_ERROR "Unsupported locked architecture")
    endif()
    message(STATUS "Deployment profile: ${DIFFUSION_DEPLOY_LOCK_PROFILE}")
    message(STATUS "Platform lock SHA256: ${DIFFUSION_DEPLOY_LOCK_SHA256}")
endif()

# Export compile_commands.json for IDE tooling (clangd, VSCode IntelliSense)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Build options
option(USE_TORCH         "Build with LibTorch backend"       OFF)
option(USE_ONNX          "Build with ONNXRuntime backend"    OFF)
option(USE_UNITREE_SDK2  "Enable Unitree SDK2 DDS channels"  OFF)
option(USE_FK            "Build with Pinocchio FK"           OFF)
option(BUILD_TOOLS       "Build debug and benchmark tools"   OFF)
option(BUILD_DDIM5_OPT_TOOLS "Build Task082 DDIM5 profiling tools" OFF)
option(BUILD_EDGE_PREFLIGHT "Build read-only edge diagnostics" OFF)
option(EDGE_MINIMAL      "Build the minimal headless edge surface" OFF)
option(ENABLE_UNITREE_COMMAND_PUBLISH "Enable robot command publishing" OFF)

if(ENABLE_UNITREE_COMMAND_PUBLISH AND NOT USE_UNITREE_SDK2)
    message(FATAL_ERROR
        "ENABLE_UNITREE_COMMAND_PUBLISH requires USE_UNITREE_SDK2=ON")
endif()

if(EDGE_MINIMAL)
    set(BUILD_TOOLS OFF CACHE BOOL "Build debug and benchmark tools" FORCE)
    set(BUILD_TESTING OFF CACHE BOOL "Build tests" FORCE)
endif()

# ---- Dependencies ----
find_package(yaml-cpp REQUIRED)
find_package(Eigen3 REQUIRED NO_MODULE)
find_package(Threads REQUIRED)
find_package(fmt CONFIG QUIET)

# LibTorch is required for any inference backend.
# Use -DCMAKE_PREFIX_PATH=/path/to/libtorch or set via build.sh.
if(USE_TORCH OR USE_ONNX)
    find_package(Torch REQUIRED)
    message(STATUS "LibTorch found: ${TORCH_INSTALL_PREFIX}")
    if(DEPLOY_PROFILE AND NOT Torch_VERSION VERSION_EQUAL DIFFUSION_DEPLOY_EXPECTED_TORCH)
        message(FATAL_ERROR
            "Locked Torch version ${DIFFUSION_DEPLOY_EXPECTED_TORCH}, found ${Torch_VERSION}")
    endif()
endif()

if(USE_ONNX)
    # Allow specifying the ONNX Runtime root via -DONNXRUNTIME_ROOT=...
    if(DEFINED ONNXRUNTIME_ROOT)
        set(onnxruntime_INCLUDE_DIRS "${ONNXRUNTIME_ROOT}/include")
        find_library(onnxruntime_LIBRARIES NAMES onnxruntime
            PATHS "${ONNXRUNTIME_ROOT}/lib" NO_DEFAULT_PATH)
        if(NOT onnxruntime_LIBRARIES)
            message(FATAL_ERROR "onnxruntime library not found in ${ONNXRUNTIME_ROOT}/lib")
        endif()
        add_library(onnxruntime::onnxruntime SHARED IMPORTED)
        set_target_properties(onnxruntime::onnxruntime PROPERTIES
            IMPORTED_LOCATION "${onnxruntime_LIBRARIES}"
            INTERFACE_INCLUDE_DIRECTORIES "${onnxruntime_INCLUDE_DIRS}")
        message(STATUS "ONNX Runtime found at ${ONNXRUNTIME_ROOT}")
    else()
        find_package(onnxruntime REQUIRED)
    endif()
endif()

if(USE_FK)
    # FK uses stable Pinocchio 2.6 APIs and is compatible with newer 2.x builds.
    find_package(pinocchio 2.6.21 CONFIG REQUIRED)
    message(STATUS "Pinocchio FK package: ${pinocchio_DIR}")
endif()

# Prefer the SDK's CMake config; target images may instead provide a flat
# headers/static-library/CycloneDDS prefix without unitree_sdk2Config.cmake.
# Installed by scripts/inst_deploy.sh to /opt/unitree_robotics.
# Override the search path via -DUNITREE_SDK2_PATH=... or $UNITREE_SDK2_PATH env var.
if(USE_UNITREE_SDK2)
    find_package(spdlog 1.15 CONFIG REQUIRED)
    if(DEFINED ENV{UNITREE_SDK2_PATH})
        set(_sdk2_root "$ENV{UNITREE_SDK2_PATH}")
    elseif(DEFINED UNITREE_SDK2_PATH)
        set(_sdk2_root "${UNITREE_SDK2_PATH}")
    else()
        set(_sdk2_root "/opt/unitree_robotics")
    endif()

    include(cmake/ResolveUnitreeSDK2.cmake)
    diffusion_deploy_resolve_unitree_sdk2("${_sdk2_root}")
    message(STATUS "unitree_sdk2 found at ${_sdk2_root}")
endif()

# ---- Source files ----
# All sources except math_utils depend on LibTorch (tensors throughout).
# Baseline build (no backend) compiles only math_utils for a quick sanity check.
# Use --backend torch or --backend onnx for a full build.
set(DIFFUSION_DEPLOY_SOURCES
    src/utils/math_utils.cpp
    src/command/unified_command_interface.cpp
    src/safety/unitree_remote_adapter.cpp
)

if(USE_TORCH OR USE_ONNX)
    list(APPEND DIFFUSION_DEPLOY_SOURCES
        src/obs/obs_terms.cpp
        src/obs/obs_composer.cpp
        src/env/unitree_env.cpp
        src/agent/diffusion_agent.cpp
        src/runner/env_runner.cpp
        src/runner/csv_recorder.cpp
        src/runner/env_runner_debug.cpp
        src/utils/normalizer.cpp
        src/utils/obs_history.cpp
        src/utils/config_parser.cpp
    )
endif()

if(USE_TORCH)
    list(APPEND DIFFUSION_DEPLOY_SOURCES
        src/actor/torch_actor.cpp
        src/actor/diffusion_actor.cpp
        src/actor/joint_diffusion_actor.cpp
        src/actor/diffuse_cloc_actor.cpp
        src/guidance/whole_body_guidance.cpp
    )
endif()

if(USE_ONNX)
    list(APPEND DIFFUSION_DEPLOY_SOURCES
        src/actor/onnx_actor.cpp
    )
endif()

# ---- Library target ----
add_library(diffusion_deploy SHARED ${DIFFUSION_DEPLOY_SOURCES})

target_include_directories(diffusion_deploy PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)

target_link_libraries(diffusion_deploy PUBLIC
    yaml-cpp
    Eigen3::Eigen
    Threads::Threads
)

if(USE_TORCH OR USE_ONNX)
    target_link_libraries(diffusion_deploy PUBLIC ${TORCH_LIBRARIES})
endif()

if(USE_TORCH)
    target_compile_definitions(diffusion_deploy PUBLIC USE_TORCH)
    add_executable(check_backbone_device_parity
        tools/check_backbone_device_parity.cpp)
    target_link_libraries(check_backbone_device_parity diffusion_deploy)
endif()

if(USE_ONNX)
    target_link_libraries(diffusion_deploy PUBLIC onnxruntime::onnxruntime)
    target_compile_definitions(diffusion_deploy PUBLIC USE_ONNX)
endif()

if(USE_UNITREE_SDK2)
    # unitree_sdk2 target links ddsc/ddscxx (CycloneDDS) transitively.
    # The SDK publisher headers pull in spdlog after Torch's bundled fmt 11.
    # Keep that integration header-only so no compiled fmt 9/11 ABI is mixed.
    if(NOT TARGET fmt::fmt)
        message(FATAL_ERROR "USE_UNITREE_SDK2 requires locked fmt::fmt")
    endif()
    target_link_libraries(diffusion_deploy PUBLIC
        unitree_sdk2 fmt::fmt spdlog::spdlog_header_only)
    target_compile_definitions(diffusion_deploy PRIVATE FMT_HEADER_ONLY)
    target_compile_definitions(diffusion_deploy PUBLIC HAVE_UNITREE_SDK2)
endif()

if(ENABLE_UNITREE_COMMAND_PUBLISH)
    target_compile_definitions(diffusion_deploy PUBLIC ENABLE_UNITREE_COMMAND_PUBLISH)
    message(WARNING
        "Building a motor-command-capable binary (rt/lowcmd publishing enabled)")
endif()

if(USE_FK)
    target_link_libraries(diffusion_deploy PUBLIC pinocchio::pinocchio)
    target_compile_definitions(diffusion_deploy PUBLIC USE_FK)
    target_sources(diffusion_deploy PRIVATE src/utils/g1_fk.cpp)
endif()

# ---- Executables ----
if(USE_TORCH OR USE_ONNX)
    add_executable(run_g1_robot examples/run_g1_robot.cpp)
    target_link_libraries(run_g1_robot diffusion_deploy)

    if(BUILD_EDGE_PREFLIGHT)
        add_executable(inspect_edge_deploy tools/inspect_edge_deploy.cpp)
        target_link_libraries(inspect_edge_deploy diffusion_deploy)
        add_executable(benchmark_g1_feedback tools/benchmark_g1_feedback.cpp)
        target_link_libraries(benchmark_g1_feedback diffusion_deploy)
        # The Task142 benchmark has a compile-time no-publish guard.  Keep it
        # out of control-capable builds while retaining it in validation builds.
        if(NOT ENABLE_UNITREE_COMMAND_PUBLISH)
            add_executable(benchmark_task142_orin tools/benchmark_task142_orin.cpp)
            target_link_libraries(benchmark_task142_orin diffusion_deploy)
            if(TARGET torch_cuda)
                target_compile_definitions(
                    benchmark_task142_orin PRIVATE DIFFUSION_DEPLOY_TORCH_CUDA)
            endif()
        endif()
        add_executable(probe_unitree_remote tools/probe_unitree_remote.cpp)
        target_link_libraries(probe_unitree_remote diffusion_deploy)
    endif()

    if(BUILD_TESTING)
        add_executable(test_unitree_env test/test_unitree_env.cpp)
        target_link_libraries(test_unitree_env diffusion_deploy)
        add_executable(test_unitree_no_publish test/test_unitree_no_publish.cpp)
        target_link_libraries(test_unitree_no_publish diffusion_deploy)
        add_test(NAME unitree_no_publish_runtime COMMAND test_unitree_no_publish)
        add_executable(test_normalizer test/test_normalizer/test_normalizer.cpp)
        target_link_libraries(test_normalizer diffusion_deploy)
        add_executable(test_prdp_wbg test/test_prdp_wbg/test_prdp_wbg.cpp)
        target_link_libraries(test_prdp_wbg diffusion_deploy)
        add_executable(test_prdp_contract test/test_prdp_contract/test_prdp_contract.cpp)
        target_link_libraries(test_prdp_contract diffusion_deploy)
        add_executable(test_standard2_condition test/test_prdp_contract/test_standard2_condition.cpp)
        target_link_libraries(test_standard2_condition diffusion_deploy)
        add_test(NAME standard2_condition COMMAND test_standard2_condition)
        add_executable(test_config_parser test/test_config_parser/test_config_parser.cpp)
        target_link_libraries(test_config_parser diffusion_deploy)
        add_test(NAME config_parser COMMAND test_config_parser)
        # Keep this test independent from the deployment shared library.  The
        # full FK-enabled library may load third-party octomap finalizers that
        # are unrelated to CSV recording and can fail during process teardown.
        add_executable(test_csv_recorder
            test/test_csv_recorder.cpp
            src/runner/csv_recorder.cpp)
        target_include_directories(test_csv_recorder PRIVATE include)
        target_link_libraries(test_csv_recorder ${TORCH_LIBRARIES} yaml-cpp)
        add_test(NAME csv_recorder COMMAND test_csv_recorder)
        add_executable(test_wbg_udp test/test_prdp_wbg/test_wbg_udp.cpp)
        target_link_libraries(test_wbg_udp diffusion_deploy)
        add_executable(test_wbg_axis_fusion
            test/test_prdp_wbg/test_wbg_axis_fusion.cpp)
        target_link_libraries(test_wbg_axis_fusion diffusion_deploy)
        add_test(NAME wbg_axis_fusion COMMAND test_wbg_axis_fusion)
        add_executable(test_ddim_step_parity test/test_prdp_wbg/test_ddim_step_parity.cpp)
        target_link_libraries(test_ddim_step_parity diffusion_deploy)
    endif()

    if(BUILD_TOOLS)
        add_executable(run_debug test/run_debug/run_debug.cpp)
        target_link_libraries(run_debug diffusion_deploy)
        add_executable(test_agent_parity test/test_agent_parity/test_agent_parity.cpp)
        target_link_libraries(test_agent_parity diffusion_deploy)
        add_executable(audit_backbone_runtime tools/audit_backbone_runtime.cpp)
        target_link_libraries(audit_backbone_runtime diffusion_deploy)
        add_executable(benchmark_prdp_wbg test/test_prdp_wbg/benchmark_prdp_wbg.cpp)
        target_link_libraries(benchmark_prdp_wbg diffusion_deploy)
        add_executable(benchmark_wbg_axis_fusion
            tools/benchmark_wbg_axis_fusion.cpp)
        target_link_libraries(benchmark_wbg_axis_fusion diffusion_deploy)
        if(TARGET torch_cuda)
            target_compile_definitions(
                benchmark_wbg_axis_fusion PRIVATE DIFFUSION_DEPLOY_TORCH_CUDA)
        endif()
        add_executable(benchmark_wbg_axis_policy
            tools/benchmark_wbg_axis_policy.cpp)
        target_link_libraries(benchmark_wbg_axis_policy diffusion_deploy)
        add_executable(check_ns_ddim_fast_wbg
            tools/check_ns_ddim_fast_wbg.cpp)
        target_link_libraries(check_ns_ddim_fast_wbg diffusion_deploy)
        if(TARGET torch_cuda)
            target_compile_definitions(
                benchmark_wbg_axis_policy PRIVATE DIFFUSION_DEPLOY_TORCH_CUDA)
        endif()
        if(BUILD_DDIM5_OPT_TOOLS)
            add_executable(benchmark_ddim5_optimization tools/benchmark_ddim5_optimization.cpp)
            target_link_libraries(benchmark_ddim5_optimization diffusion_deploy)
            if(TARGET torch_cuda)
                target_compile_definitions(
                    benchmark_ddim5_optimization PRIVATE DIFFUSION_DEPLOY_TORCH_CUDA)
            endif()
        endif()
        add_executable(benchmark_production_profile tools/benchmark_production_profile.cpp)
        target_link_libraries(benchmark_production_profile diffusion_deploy)
        if(TARGET torch_cuda)
            target_compile_definitions(
                benchmark_production_profile PRIVATE DIFFUSION_DEPLOY_TORCH_CUDA)
        endif()
    endif()
endif()
if(BUILD_TESTING)
    find_package(Python3 3.8 COMPONENTS Interpreter REQUIRED)
    add_test(NAME task142_source_guard
        COMMAND ${Python3_EXECUTABLE}
                ${CMAKE_CURRENT_SOURCE_DIR}/test/test_task142_source_guard.py)
    add_executable(test_unified_command test/test_unified_command.cpp)
    target_link_libraries(test_unified_command diffusion_deploy)
    add_test(NAME unified_command COMMAND test_unified_command)
    add_test(NAME unified_command_protocol
        COMMAND ${Python3_EXECUTABLE}
                ${CMAKE_CURRENT_SOURCE_DIR}/test/test_unified_command_protocol.py)
    add_test(NAME unified_command_source_safety
        COMMAND bash ${CMAKE_CURRENT_SOURCE_DIR}/test/test_unified_command_source_safety.sh
                ${CMAKE_CURRENT_SOURCE_DIR})
    add_executable(test_action_selection test/test_action_selection.cpp)
    target_include_directories(test_action_selection PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/include)
    add_test(NAME action_selection COMMAND test_action_selection)
    add_test(NAME model_resource_isolation
        COMMAND bash ${CMAKE_CURRENT_SOURCE_DIR}/test/test_model_resource_isolation.sh
                ${CMAKE_CURRENT_SOURCE_DIR})
    add_test(NAME edge_bundle
        COMMAND bash ${CMAKE_CURRENT_SOURCE_DIR}/test/test_edge_bundle.sh
                ${CMAKE_CURRENT_SOURCE_DIR} ${CMAKE_BINARY_DIR})
    add_test(NAME unitree_no_publish_source
        COMMAND bash ${CMAKE_CURRENT_SOURCE_DIR}/test/test_unitree_no_publish_source.sh
                ${CMAKE_CURRENT_SOURCE_DIR})
    add_test(NAME unitree_sdk2_discovery
        COMMAND bash ${CMAKE_CURRENT_SOURCE_DIR}/test/test_unitree_sdk2_discovery.sh
                ${CMAKE_CURRENT_SOURCE_DIR} ${CMAKE_BINARY_DIR})
    add_test(NAME deploy_manager
        COMMAND ${Python3_EXECUTABLE}
                ${CMAKE_CURRENT_SOURCE_DIR}/test/test_deploy_manager.py)
    add_test(NAME task164_session_materializer
        COMMAND ${Python3_EXECUTABLE}
                ${CMAKE_CURRENT_SOURCE_DIR}/test/test_task164_session_materializer.py)
    add_test(NAME task165_wbg_contract
        COMMAND ${Python3_EXECUTABLE}
                ${CMAKE_CURRENT_SOURCE_DIR}/test/test_task165_wbg_contract.py)
    add_test(NAME g1_urdf_resource
        COMMAND ${Python3_EXECUTABLE}
                ${CMAKE_CURRENT_SOURCE_DIR}/test/test_g1_urdf_resource.py)
    add_test(NAME jp5_build_routing
        COMMAND bash ${CMAKE_CURRENT_SOURCE_DIR}/test/test_jp5_build_routing.sh
                ${CMAKE_CURRENT_SOURCE_DIR})
    add_test(NAME g1_feedback_benchmark_source
        COMMAND bash ${CMAKE_CURRENT_SOURCE_DIR}/test/test_g1_feedback_benchmark_source.sh
                ${CMAKE_CURRENT_SOURCE_DIR})
    add_test(NAME wbg_axis_fusion_source_safety
        COMMAND bash ${CMAKE_CURRENT_SOURCE_DIR}/test/test_wbg_axis_fusion_source_safety.sh
                ${CMAKE_CURRENT_SOURCE_DIR})
    add_test(NAME production_profile_source
        COMMAND bash ${CMAKE_CURRENT_SOURCE_DIR}/test/test_production_profile_source.sh
                ${CMAKE_CURRENT_SOURCE_DIR})
endif()

# ---- Install ----
install(TARGETS diffusion_deploy
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)
if(TARGET run_g1_robot)
    install(TARGETS run_g1_robot RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})
endif()
if(TARGET inspect_edge_deploy)
    install(TARGETS inspect_edge_deploy RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})
endif()
if(TARGET benchmark_g1_feedback)
    install(TARGETS benchmark_g1_feedback RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})
endif()
if(NOT EDGE_MINIMAL)
    install(DIRECTORY include/ DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
endif()
install(FILES config/g1_edge_minimal.yaml config/fsm_unitree_remote.yaml
    DESTINATION ${CMAKE_INSTALL_DATADIR}/diffusion_deploy/config)
install(FILES resources/g1/main.urdf resources/g1/PROVENANCE.md
    resources/g1/LICENSE resources/g1/SOURCE_PACKAGE.xml
    DESTINATION ${CMAKE_INSTALL_DATADIR}/diffusion_deploy/resources/g1)
install(FILES doc/PREDATOR_DEPLOYMENT.md
    doc/POLICY_EXPORT_AND_CONFIG.md doc/WORKSTATION_BUILD.md
    DESTINATION ${CMAKE_INSTALL_DATADIR}/diffusion_deploy/doc)
install(FILES doc/G1OnboardDeployDoc/PUBLIC_ONBOARD.md
    DESTINATION ${CMAKE_INSTALL_DATADIR}/diffusion_deploy/doc/G1OnboardDeployDoc)
install(PROGRAMS scripts/create_edge_bundle.sh scripts/verify_model_resources.sh
    DESTINATION ${CMAKE_INSTALL_DATADIR}/diffusion_deploy/scripts)
