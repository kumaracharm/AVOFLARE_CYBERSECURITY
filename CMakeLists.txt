cmake_minimum_required(VERSION 3.10)
project(UavSecStack VERSION 1.0)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED True)

# Add include directories
include_directories(include)

# Gather source files
file(GLOB_RECURSE SOURCES "src/*.c")

# Create a static library for the security stack
add_library(uav_sec_stack STATIC ${SOURCES})

# Add tests if CTest is enabled
enable_testing()

add_executable(test_crypto tests/test_crypto.c)
target_link_libraries(test_crypto uav_sec_stack)
add_test(NAME test_crypto COMMAND test_crypto)

add_executable(test_replay tests/test_replay.c)
target_link_libraries(test_replay uav_sec_stack)
add_test(NAME test_replay COMMAND test_replay)

add_executable(test_framing tests/test_framing.c)
target_link_libraries(test_framing uav_sec_stack)
add_test(NAME test_framing COMMAND test_framing)
