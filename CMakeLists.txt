cmake_minimum_required(VERSION 3.16)

project(surrogated-assisted-optimizer
    VERSION 1.0
    LANGUAGES CXX
)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)


# --------------------
# AUX library
# --------------------

add_library(aux
    source/aux/aux.cpp
    source/aux/network_files.cpp
)

target_include_directories(aux
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/source/aux/include
)


# --------------------
# PSO library
# --------------------

add_library(pso
    source/pso/pso.cpp
)

target_include_directories(pso
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/source/pso/include
)

target_link_libraries(pso
    PUBLIC
        aux
)


# --------------------
# Application
# --------------------

add_executable(surrogated-assisted-optimizer
    source/app.cpp
)

target_include_directories(surrogated-assisted-optimizer
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/source/include
)

target_link_libraries(surrogated-assisted-optimizer
    PRIVATE
        pso
)