#pragma once

#include <unordered_map>
#include "pso.h"
#include "aux.h"

using OptimizerFunction = int (*)(int, char*[], Scenario&);

int initPso(int argc, char* argv[], Scenario& scenario);

const std::unordered_map<std::string_view, OptimizerFunction> optimizers = {
    {"pso", initPso}
};