# Resolve Unitree SDK2 without assuming that its optional CMake package was
# installed.  Unitree's target images commonly contain only a flat prefix:
# headers, libunitree_sdk2.a, and the CycloneDDS shared libraries.
function(diffusion_deploy_resolve_unitree_sdk2 sdk2_root)
    if(TARGET unitree_sdk2)
        return()
    endif()

    # Prefer the SDK-provided package whenever it is present.  Keep the search
    # scoped to the selected target prefix so host SDKs cannot leak into an
    # aarch64 deployment build.
    set(_sdk2_config_hints
        "${sdk2_root}/lib/cmake/unitree_sdk2"
        "${sdk2_root}/lib64/cmake/unitree_sdk2"
        "${sdk2_root}/lib/aarch64-linux-gnu/cmake/unitree_sdk2")
    if(DEFINED unitree_sdk2_DIR AND NOT unitree_sdk2_DIR STREQUAL "")
        list(PREPEND _sdk2_config_hints "${unitree_sdk2_DIR}")
    endif()
    find_package(unitree_sdk2 CONFIG QUIET
        PATHS ${_sdk2_config_hints}
        NO_DEFAULT_PATH)
    if(unitree_sdk2_FOUND)
        if(NOT TARGET unitree_sdk2)
            message(FATAL_ERROR
                "unitree_sdk2Config.cmake was found but did not define target unitree_sdk2")
        endif()
        message(STATUS "Unitree SDK2: config package (${unitree_sdk2_DIR})")
        return()
    endif()

    if(DEFINED UNITREE_CYCLONEDDS_PATH AND NOT UNITREE_CYCLONEDDS_PATH STREQUAL "")
        set(_cyclonedds_root "${UNITREE_CYCLONEDDS_PATH}")
    else()
        set(_cyclonedds_root "${sdk2_root}")
    endif()

    set(_sdk2_library_hints
        "${sdk2_root}/lib"
        "${sdk2_root}/lib64"
        "${sdk2_root}/lib/aarch64"
        "${sdk2_root}/lib/x86_64"
        "${sdk2_root}/lib/aarch64-linux-gnu")
    set(_cyclonedds_library_hints
        "${_cyclonedds_root}/lib"
        "${_cyclonedds_root}/lib64"
        "${_cyclonedds_root}/lib/aarch64-linux-gnu")
    find_path(_sdk2_include_dir
        NAMES unitree/robot/channel/channel_factory.hpp
        PATHS "${sdk2_root}/include"
        NO_DEFAULT_PATH)
    find_path(_sdk2_ddscxx_include_dir
        NAMES dds/dds.hpp
        PATHS "${_cyclonedds_root}/include/ddscxx"
        NO_DEFAULT_PATH)
    find_file(_sdk2_archive
        NAMES libunitree_sdk2.a
        PATHS ${_sdk2_library_hints}
        NO_DEFAULT_PATH)
    find_library(_sdk2_ddsc_library
        NAMES ddsc
        PATHS ${_cyclonedds_library_hints}
        NO_DEFAULT_PATH)
    find_library(_sdk2_ddscxx_library
        NAMES ddscxx
        PATHS ${_cyclonedds_library_hints}
        NO_DEFAULT_PATH)

    set(_sdk2_missing "")
    foreach(_pair IN ITEMS
            "headers|${_sdk2_include_dir}"
            "CycloneDDS C++ headers|${_sdk2_ddscxx_include_dir}"
            "libunitree_sdk2.a|${_sdk2_archive}"
            "libddsc|${_sdk2_ddsc_library}"
            "libddscxx|${_sdk2_ddscxx_library}")
        string(REPLACE "|" ";" _fields "${_pair}")
        list(GET _fields 0 _label)
        list(GET _fields 1 _path)
        if(NOT _path OR _path MATCHES "-NOTFOUND$")
            list(APPEND _sdk2_missing "${_label}")
        endif()
    endforeach()
    if(_sdk2_missing)
        list(JOIN _sdk2_missing ", " _sdk2_missing_text)
        message(FATAL_ERROR
            "Unitree SDK2 config package is absent and flat prefix ${sdk2_root} "
            "is incomplete (missing: ${_sdk2_missing_text})")
    endif()

    add_library(unitree_sdk2_ddsc UNKNOWN IMPORTED GLOBAL)
    set_target_properties(unitree_sdk2_ddsc PROPERTIES
        IMPORTED_LOCATION "${_sdk2_ddsc_library}")
    add_library(unitree_sdk2_ddscxx UNKNOWN IMPORTED GLOBAL)
    set_target_properties(unitree_sdk2_ddscxx PROPERTIES
        IMPORTED_LOCATION "${_sdk2_ddscxx_library}"
        INTERFACE_INCLUDE_DIRECTORIES "${_sdk2_ddscxx_include_dir}"
        INTERFACE_LINK_LIBRARIES unitree_sdk2_ddsc)
    add_library(unitree_sdk2 STATIC IMPORTED GLOBAL)
    set_target_properties(unitree_sdk2 PROPERTIES
        IMPORTED_LOCATION "${_sdk2_archive}"
        INTERFACE_INCLUDE_DIRECTORIES "${_sdk2_include_dir}"
        INTERFACE_LINK_LIBRARIES "unitree_sdk2_ddscxx;unitree_sdk2_ddsc")
    message(STATUS "Unitree SDK2: flat target prefix (${sdk2_root})")
endfunction()
