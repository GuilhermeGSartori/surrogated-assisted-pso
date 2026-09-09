#pragma once

#include "aux.h"

#include <string>

void appendNodes(const std::vector<Coordinates>& nodes, std::string& packet, int n_clusters);
std::string generatePacket(const FixedSizeVector<Coordinates>& relays, const Scenario& scenario);
double sendPacket(const std::string& packet);
