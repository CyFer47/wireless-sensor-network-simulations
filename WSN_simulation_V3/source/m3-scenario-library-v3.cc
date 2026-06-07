#include "ns3/core-module.h"
#include "ns3/mobility-module.h"
#include "ns3/network-module.h"

#include <algorithm>
#include <cctype>
#include <cstdint>
#include <ctime>
#include <deque>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <numeric>
#include <queue>
#include <sstream>
#include <string>
#include <vector>
#include <cmath>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("M3ScenarioLibrary");

namespace
{

struct ScaleRule
{
    uint32_t nodeCount;
    uint32_t chCount;
    uint32_t bsCount;
    double widthM;
    double heightM;
};

struct NodeRow
{
    uint32_t nodeId{};
    double x{};
    double y{};
};

struct ChRow
{
    uint32_t chId{};
    uint32_t nodeId{};
    double x{};
    double y{};
};

struct BsRow
{
    uint32_t bsId{};
    double x{};
    double y{};
};

struct ClusterDef
{
    uint32_t clusterId{};
    uint32_t chNodeId{};
    std::vector<uint32_t> members;
    uint32_t currentChNodeId{};
    uint32_t defaultBsId{};
    bool failed{false};
    bool recovered{false};
    bool overloaded{false};
    double loadFactor{1.0};
    double linkQuality{1.0};
    uint32_t pendingRaw{0};
    uint64_t rawTx{0};
    uint64_t rawRx{0};
    uint64_t aggTx{0};
    uint64_t relayFwd{0};
    uint64_t dropped{0};
    uint32_t rerouteViaClusterId{std::numeric_limits<uint32_t>::max()};
    uint32_t rerouteBsId{std::numeric_limits<uint32_t>::max()};
    bool rerouteActive{false};
};

struct GlobalSnapshot
{
    double simTime{};
    uint64_t rawTx{};
    uint64_t rawRx{};
    uint64_t aggTx{};
    uint64_t aggRx{};
    uint64_t directAggRx{};
    uint64_t relayedAggRx{};
    uint64_t relayFwd{};
    uint32_t lowNodes{};
    uint32_t failedChs{};
    uint32_t recoveredClusters{};
    uint64_t pendingRawTotal{};
    double avgResJ{};
    double minResJ{};
    double consumedJ{};
};

struct ClusterSnapshot
{
    double simTime{};
    uint32_t clusterId{};
    uint32_t originalChId{};
    uint32_t currentChId{};
    std::string status;
    std::string mode;
    std::string nextHop;
    uint32_t membersCount{};
    uint64_t rawRx{};
    uint32_t pendingRaw{};
    uint64_t aggTx{};
    uint64_t relayFwd{};
    double chResJ{};
    double avgMemResJ{};
    double clusterConsumedJ{};
};

struct EventRow
{
    double simTime{};
    std::string eventType;
    std::string severity;
    int clusterId{-1};
    int nodeId{-1};
    std::string message;
    std::string detailsJson{"{}"};
};

struct RunState
{
    std::string runSpecId;
    std::string mapId;
    std::string mapSignature;
    std::string architecture;
    std::string variant;
    std::string failureFamily;
    std::string healingId;
    std::string load;
    std::string scale;
    uint32_t seed{};
    double simTime{};
    double trafficInterval{};
    double aggregationInterval{};
    double dashboardInterval{};
    double failureTime{};
    double recoveryDelay{};
    double recoveryAppliedDelayS{-1.0};
    double recoveryAppliedTimeS{-1.0};
    double recoveryEventTimeS{-1.0};
    double firstRecoveredAggregateS{-1.0};
    double recoveryStressScore{0.0};
    double recoveryMapProfilePenaltyS{0.0};
    double recoveryQueueNorm{0.0};
    double recoveryClusterNorm{0.0};
    double recoveryEnergyNorm{0.0};
    double recoveryDistanceNorm{0.0};
    bool recoveryScheduled{false};
    bool enableFailure{};
    bool enableRecovery{};
    bool enableRunExport{true};
    std::string exportRootDir{"outputs"};
    std::string exportRunLabel;
    std::string simSource{"test-ns3/m3-scenario-library.cc"};
    uint32_t nodeCount{};
    uint32_t clusterCount{};
    uint32_t bsCount{};
    double areaWidth{};
    double areaHeight{};
    uint32_t targetClusterId{};
    uint32_t relaySourceClusterId{};
    uint32_t relayViaClusterId{};
    uint32_t targetRecoveryClusterId{};
    double loadMultiplier{1.0};
};

constexpr double kBoundaryMarginM = 2.0;
constexpr uint32_t kInvalidId = std::numeric_limits<uint32_t>::max();

const std::map<std::string, ScaleRule> kScaleRules = {
    {"S1", {50, 3, 1, 100.0, 100.0}},
    {"S2", {100, 6, 1, 150.0, 150.0}},
    {"S3", {200, 10, 1, 220.0, 220.0}},
    {"S4", {400, 20, 1, 320.0, 320.0}},
    {"S5", {800, 32, 2, 450.0, 450.0}},
    {"S6", {1600, 64, 3, 640.0, 640.0}},
    {"S7", {3200, 128, 4, 920.0, 920.0}},
    {"S8", {4000, 160, 5, 1020.0, 1020.0}},
    {"S9", {4500, 180, 6, 1080.0, 1080.0}},
    {"S10", {5000, 200, 6, 1150.0, 1150.0}},
};

std::vector<NodeRow> gNodes;
std::vector<ChRow> gChRows;
std::vector<BsRow> gBsRows;
std::vector<ClusterDef> gClusters;
std::vector<double> gResidualJ;
std::vector<double> gConsumedJ;
std::vector<uint32_t> gNodeToCluster;
std::vector<GlobalSnapshot> gGlobalSnapshots;
std::vector<ClusterSnapshot> gClusterSnapshots;
std::vector<EventRow> gEvents;
RunState gState;
std::deque<std::string> gRecentEvents;
uint64_t gGlobalRawTx{};
uint64_t gGlobalRawRx{};
uint64_t gGlobalAggTx{};
uint64_t gGlobalAggRx{};
uint64_t gGlobalDirectAggRx{};
uint64_t gGlobalRelayedAggRx{};
uint64_t gGlobalRelayFwd{};

static std::string Trim(std::string s)
{
    auto notSpace = [](unsigned char c) { return !std::isspace(c); };
    s.erase(s.begin(), std::find_if(s.begin(), s.end(), notSpace));
    s.erase(std::find_if(s.rbegin(), s.rend(), notSpace).base(), s.end());
    return s;
}

static std::vector<std::string> SplitCsv(const std::string& line)
{
    std::vector<std::string> cols;
    std::string cur;
    bool inQuote = false;
    for (char c : line)
    {
        if (c == '"')
        {
            inQuote = !inQuote;
            continue;
        }
        if (c == ',' && !inQuote)
        {
            cols.push_back(cur);
            cur.clear();
            continue;
        }
        cur.push_back(c);
    }
    cols.push_back(cur);
    for (auto& s : cols)
    {
        s = Trim(s);
    }
    return cols;
}

static std::vector<NodeRow> LoadNodesCsv(const std::filesystem::path& path)
{
    std::ifstream f(path);
    if (!f)
    {
        throw std::runtime_error("Unable to open nodes.csv: " + path.string());
    }
    std::string line;
    std::getline(f, line); // header
    std::vector<NodeRow> rows;
    while (std::getline(f, line))
    {
        if (line.empty())
        {
            continue;
        }
        auto cols = SplitCsv(line);
        if (cols.size() < 3)
        {
            continue;
        }
        rows.push_back({static_cast<uint32_t>(std::stoul(cols[0])), std::stod(cols[1]), std::stod(cols[2])});
    }
    return rows;
}

static std::vector<ChRow> LoadChBsCsv(const std::filesystem::path& path, std::vector<BsRow>& bsRows)
{
    std::ifstream f(path);
    if (!f)
    {
        throw std::runtime_error("Unable to open ch_bs.csv: " + path.string());
    }
    std::string line;
    std::getline(f, line); // header
    std::vector<ChRow> rows;
    while (std::getline(f, line))
    {
        if (line.empty())
        {
            continue;
        }
        auto cols = SplitCsv(line);
        if (cols.size() < 5)
        {
            continue;
        }
        const std::string& type = cols[0];
        if (type == "CH")
        {
            rows.push_back({static_cast<uint32_t>(std::stoul(cols[1])), static_cast<uint32_t>(std::stoul(cols[2])), std::stod(cols[3]), std::stod(cols[4])});
        }
        else if (type == "BS")
        {
            bsRows.push_back({static_cast<uint32_t>(std::stoul(cols[1])), std::stod(cols[3]), std::stod(cols[4])});
        }
    }
    return rows;
}

static std::vector<std::pair<uint32_t, uint32_t>> LoadNodeClusterMap(const std::filesystem::path& path)
{
    std::ifstream f(path);
    if (!f)
    {
        throw std::runtime_error("Unable to open node_cluster_map.csv: " + path.string());
    }
    std::string line;
    std::getline(f, line);
    std::vector<std::pair<uint32_t, uint32_t>> rows;
    while (std::getline(f, line))
    {
        if (line.empty())
        {
            continue;
        }
        auto cols = SplitCsv(line);
        if (cols.size() < 3)
        {
            continue;
        }
        rows.emplace_back(static_cast<uint32_t>(std::stoul(cols[0])), static_cast<uint32_t>(std::stoul(cols[1])));
    }
    return rows;
}

static std::string JsonEscape(const std::string& s)
{
    std::ostringstream os;
    for (char c : s)
    {
        switch (c)
        {
        case '\\': os << "\\\\"; break;
        case '"': os << "\\\""; break;
        case '\n': os << "\\n"; break;
        case '\r': os << "\\r"; break;
        case '\t': os << "\\t"; break;
        default: os << c; break;
        }
    }
    return os.str();
}

static std::string CsvEscape(const std::string& s)
{
    if (s.find_first_of(",\"\n") == std::string::npos)
    {
        return s;
    }
    std::string out = "\"";
    for (char c : s)
    {
        if (c == '"')
        {
            out += "\"\"";
        }
        else
        {
            out.push_back(c);
        }
    }
    out += '"';
    return out;
}

static void AddEvent(double simTime, const std::string& type, const std::string& severity, int clusterId, int nodeId, const std::string& message, const std::string& details = "{}")
{
    gEvents.push_back({simTime, type, severity, clusterId, nodeId, message, details});
    std::ostringstream os;
    os << "t=" << std::fixed << std::setprecision(3) << simTime << "s " << type << " " << message;
    gRecentEvents.push_back(os.str());
    while (gRecentEvents.size() > 8)
    {
        gRecentEvents.pop_front();
    }
}

static double LowEnergyThresholdJ()
{
    return 2.0 * 0.20;
}

static void ApplyEnergy(uint32_t nodeId, double amountJ)
{
    if (nodeId >= gResidualJ.size() || amountJ <= 0.0)
    {
        return;
    }
    const double before = gResidualJ[nodeId];
    const double delta = std::min(before, amountJ);
    gResidualJ[nodeId] = std::max(0.0, before - delta);
    gConsumedJ[nodeId] += delta;
}

static double DistanceSq(double ax, double ay, double bx, double by)
{
    const double dx = ax - bx;
    const double dy = ay - by;
    return dx * dx + dy * dy;
}
static double DistanceM(double ax,
                        double ay,
                        double bx,
                        double by)
{
    return std::sqrt(DistanceSq(ax, ay, bx, by));
}

static double MemberTxEnergy(double distanceM)
{
    const double base = 0.0008;
    const double d = distanceM / 50.0;
    const double factor = 1.0 + d + (0.50 * d * d);
    return base * factor;
}

static double ChRxEnergy(double distanceM)
{
    const double base = 0.0005;
    const double d = distanceM / 60.0;
    const double factor = 1.0 + (0.70 * d);
    return base * factor;
}

static double ChAggregationEnergy(uint32_t pending)
{
    return 0.0002 * pending;
}

static double ChToBsTxEnergy(double distanceM)
{
    const double base = 0.0012;
    const double factor = 1.0 + (distanceM / 40.0);
    return base * factor;
}

static double BaseRecoveryDelayByHealingS(const std::string& healingId)
{
    if (healingId == "H1")
    {
        return 8.0;
    }
    if (healingId == "H2")
    {
        return 12.0;
    }
    if (healingId == "H3")
    {
        return 14.0;
    }
    if (healingId == "H4")
    {
        return 18.0;
    }
    return gState.recoveryDelay;
}

static double FailurePenaltyDelayS(const std::string& failureFamily)
{
    if (failureFamily == "F1")
    {
        return 1.0;
    }
    if (failureFamily == "F2")
    {
        return 9.0;
    }
    if (failureFamily == "F3")
    {
        return 13.0;
    }
    if (failureFamily == "F4")
    {
        return 19.0;
    }
    return 0.0;
}

static double MapProfileRecoveryPenaltyS()
{
    if (gState.mapId.find("M3_IMBALANCED") != std::string::npos)
    {
        return 6.0;
    }
    if (gState.mapId.find("M2_LONG_LINK") != std::string::npos)
    {
        return 3.0;
    }
    return 0.0;
}

static uint32_t MaxClusterSize()
{
    uint32_t maxSize = 1;
    for (const auto& c : gClusters)
    {
        maxSize = std::max<uint32_t>(maxSize, static_cast<uint32_t>(c.members.size()));
    }
    return maxSize;
}

static double DistancePressureNorm(const ClusterDef& c)
{
    if (c.currentChNodeId >= gNodes.size() || gBsRows.empty())
    {
        return 0.0;
    }

    const auto* bsRow = &gBsRows.front();
    for (const auto& bs : gBsRows)
    {
        if (bs.bsId == c.defaultBsId)
        {
            bsRow = &bs;
            break;
        }
    }

    const auto& ch = gNodes[c.currentChNodeId];
    const double d = DistanceM(ch.x, ch.y, bsRow->x, bsRow->y);
    const double diag = std::sqrt(gState.areaWidth * gState.areaWidth + gState.areaHeight * gState.areaHeight);
    return std::clamp(d / std::max(1.0, diag), 0.0, 1.0);
}

static double DeterministicJitterSeconds(uint32_t seed,
                                         uint32_t clusterId,
                                         const std::string& healingId,
                                         const std::string& failureFamily)
{
    uint64_t x = 1469598103934665603ULL;
    auto mixByte = [&](uint8_t b) {
        x ^= b;
        x *= 1099511628211ULL;
    };
    auto mixString = [&](const std::string& s) {
        for (unsigned char ch : s)
        {
            mixByte(static_cast<uint8_t>(ch));
        }
    };

    for (int i = 0; i < 4; ++i)
    {
        mixByte(static_cast<uint8_t>((seed >> (8 * i)) & 0xFF));
        mixByte(static_cast<uint8_t>((clusterId >> (8 * i)) & 0xFF));
    }
    mixString(healingId);
    mixString(failureFamily);
    mixString(gState.mapSignature);

    return static_cast<double>(x % 1001ULL) / 1000.0;
}

static double ClampRecoveryDelayToSimWindow(double delayS)
{
    const double upper = std::max(1.0, gState.simTime - gState.failureTime - 0.001);
    return std::clamp(delayS, 1.0, upper);
}

static void ComputeRecoveryDelayComponents(const ClusterDef& c,
                                           double& queueNorm,
                                           double& clusterNorm,
                                           double& energyNorm,
                                           double& distanceNorm,
                                           double& stressScore)
{
    const double members = static_cast<double>(std::max<size_t>(1, c.members.size()));
    queueNorm = std::clamp(static_cast<double>(c.pendingRaw) / members, 0.0, 1.0);

    const double maxCluster = static_cast<double>(MaxClusterSize());
    clusterNorm = std::clamp(static_cast<double>(c.members.size()) / std::max(1.0, maxCluster), 0.0, 1.0);

    const double residualJ = (c.currentChNodeId < gResidualJ.size()) ? gResidualJ[c.currentChNodeId] : 2.0;
    energyNorm = std::clamp((2.0 - residualJ) / 2.0, 0.0, 1.0);

    distanceNorm = DistancePressureNorm(c);

    stressScore = 3.0 * queueNorm + 3.0 * clusterNorm + 3.0 * energyNorm + 3.0 * distanceNorm;
}

static double ComputeAppliedRecoveryDelayS(const ClusterDef& c)
{
    const double base = BaseRecoveryDelayByHealingS(gState.healingId);
    const double failurePenalty = FailurePenaltyDelayS(gState.failureFamily);
    const double mapProfilePenalty = MapProfileRecoveryPenaltyS();
    double queueNorm = 0.0;
    double clusterNorm = 0.0;
    double energyNorm = 0.0;
    double distanceNorm = 0.0;
    double stressScore = 0.0;

    ComputeRecoveryDelayComponents(c, queueNorm, clusterNorm, energyNorm, distanceNorm, stressScore);

    const double jitter = DeterministicJitterSeconds(gState.seed, c.clusterId, gState.healingId, gState.failureFamily);

    gState.recoveryQueueNorm = queueNorm;
    gState.recoveryClusterNorm = clusterNorm;
    gState.recoveryEnergyNorm = energyNorm;
    gState.recoveryDistanceNorm = distanceNorm;
    gState.recoveryStressScore = stressScore;
    gState.recoveryMapProfilePenaltyS = mapProfilePenalty;

    return ClampRecoveryDelayToSimWindow(base + failurePenalty + mapProfilePenalty + stressScore + jitter);
}

static uint32_t FindNearestBs(double x, double y)
{
    double best = std::numeric_limits<double>::max();
    uint32_t bestId = 0;
    for (const auto& bs : gBsRows)
    {
        const double d = DistanceSq(x, y, bs.x, bs.y);
        if (d < best)
        {
            best = d;
            bestId = bs.bsId;
        }
    }
    return bestId;
}

struct BsbsspRouteChoice
{
    bool reachable{false};
    bool firstHopIsBs{false};
    uint32_t firstHopClusterId{kInvalidId};
    uint32_t firstHopBsId{kInvalidId};
    double totalCost{0.0};
    std::string pathDesc;
};

static bool IsArchitectureB()
{
    return gState.architecture == "B";
}

static double NodeEnergyNorm(uint32_t nodeId)
{
    if (nodeId >= gResidualJ.size())
    {
        return 0.0;
    }
    return std::clamp(gResidualJ[nodeId] / 2.0, 0.0, 1.0);
}

static double BsbsspLinkRadiusM()
{
    const double diag = std::sqrt(gState.areaWidth * gState.areaWidth + gState.areaHeight * gState.areaHeight);
    return 0.60 * diag;
}

static std::string BsbsspNodeLabel(uint32_t graphIndex)
{
    if (graphIndex < gClusters.size())
    {
        return "C" + std::to_string(graphIndex);
    }
    return "B" + std::to_string(gBsRows[graphIndex - static_cast<uint32_t>(gClusters.size())].bsId);
}

static BsbsspRouteChoice ComputeBsbsspRoute(uint32_t sourceClusterId)
{
    BsbsspRouteChoice out;
    if (sourceClusterId >= gClusters.size() || gBsRows.empty())
    {
        return out;
    }

    const uint32_t clusterCount = static_cast<uint32_t>(gClusters.size());
    const uint32_t bsCount = static_cast<uint32_t>(gBsRows.size());
    const uint32_t totalNodes = clusterCount + bsCount;
    const double radius = BsbsspLinkRadiusM();
    const double radiusSq = radius * radius;

    std::vector<double> dist(totalNodes, std::numeric_limits<double>::max());
    std::vector<int> prev(totalNodes, -1);
    using QueueItem = std::pair<double, uint32_t>;
    std::priority_queue<QueueItem, std::vector<QueueItem>, std::greater<QueueItem>> pq;

    dist[sourceClusterId] = 0.0;
    pq.push({0.0, sourceClusterId});

    auto clusterXY = [&](uint32_t clusterId) {
        const auto& ch = gNodes[gClusters[clusterId].currentChNodeId];
        return std::pair<double, double>(ch.x, ch.y);
    };

    while (!pq.empty())
    {
        const auto [curCost, u] = pq.top();
        pq.pop();
        if (curCost > dist[u])
        {
            continue;
        }
        if (u >= clusterCount)
        {
            continue;
        }

        const auto [ux, uy] = clusterXY(u);

        for (uint32_t v = 0; v < clusterCount; ++v)
        {
            if (v == u || gClusters[v].failed)
            {
                continue;
            }
            const auto [vx, vy] = clusterXY(v);
            const double dSq = DistanceSq(ux, uy, vx, vy);
            if (dSq > radiusSq)
            {
                continue;
            }
            const double d = std::sqrt(dSq);
            const double energyPenalty = (1.0 - NodeEnergyNorm(gClusters[v].currentChNodeId)) * 0.35;
            const double queuePenalty = std::min(1.0, static_cast<double>(gClusters[v].pendingRaw) / 12.0) * 0.15;
            const double edgeCost = d * (1.0 + energyPenalty + queuePenalty);
            const double nextCost = curCost + edgeCost;
            if (nextCost < dist[v])
            {
                dist[v] = nextCost;
                prev[v] = static_cast<int>(u);
                pq.push({nextCost, v});
            }
        }

        for (uint32_t bsIdx = 0; bsIdx < bsCount; ++bsIdx)
        {
            const auto& bs = gBsRows[bsIdx];
            const double d = std::sqrt(DistanceSq(ux, uy, bs.x, bs.y));
            const double edgeCost = d * 0.90;
            const uint32_t v = clusterCount + bsIdx;
            const double nextCost = curCost + edgeCost;
            if (nextCost < dist[v])
            {
                dist[v] = nextCost;
                prev[v] = static_cast<int>(u);
                pq.push({nextCost, v});
            }
        }
    }

    uint32_t bestBsGraph = kInvalidId;
    double bestCost = std::numeric_limits<double>::max();
    for (uint32_t bsIdx = 0; bsIdx < bsCount; ++bsIdx)
    {
        const uint32_t v = clusterCount + bsIdx;
        if (dist[v] < bestCost)
        {
            bestCost = dist[v];
            bestBsGraph = v;
        }
    }

    if (bestBsGraph == kInvalidId || bestCost == std::numeric_limits<double>::max())
    {
        return out;
    }

    std::vector<uint32_t> path;
    for (int at = static_cast<int>(bestBsGraph); at >= 0; at = prev[static_cast<uint32_t>(at)])
    {
        path.push_back(static_cast<uint32_t>(at));
        if (static_cast<uint32_t>(at) == sourceClusterId)
        {
            break;
        }
    }
    std::reverse(path.begin(), path.end());
    if (path.empty() || path.front() != sourceClusterId)
    {
        return out;
    }

    out.reachable = true;
    out.totalCost = bestCost;
    if (path.size() >= 2)
    {
        const uint32_t firstHop = path[1];
        if (firstHop < clusterCount)
        {
            out.firstHopIsBs = false;
            out.firstHopClusterId = firstHop;
        }
        else
        {
            out.firstHopIsBs = true;
            out.firstHopBsId = gBsRows[firstHop - clusterCount].bsId;
        }
    }

    std::ostringstream pathOs;
    for (size_t i = 0; i < path.size(); ++i)
    {
        if (i > 0)
        {
            pathOs << "->";
        }
        pathOs << BsbsspNodeLabel(path[i]);
    }
    out.pathDesc = pathOs.str();
    return out;
}

static bool ApplyBsbsspRoute(uint32_t clusterId, const std::string& reason, bool strict)
{
    if (!IsArchitectureB() || clusterId >= gClusters.size())
    {
        return true;
    }

    auto& c = gClusters[clusterId];
    const auto route = ComputeBsbsspRoute(clusterId);
    const double now = Simulator::Now().GetSeconds();

    if (!route.reachable)
    {
        c.rerouteActive = false;
        c.rerouteViaClusterId = kInvalidId;
        c.rerouteBsId = kInvalidId;
        AddEvent(now,
                 "ROUTE_COMPUTE",
                 strict ? "ERROR" : "WARN",
                 static_cast<int>(clusterId),
                 static_cast<int>(c.currentChNodeId),
                 "BSBSSP route unavailable",
                 std::string("{\"reason\":\"") + reason + "\",\"engine\":\"BSBSSP\"}");
        return !strict;
    }

    c.rerouteActive = true;
    c.rerouteViaClusterId = route.firstHopIsBs ? kInvalidId : route.firstHopClusterId;
    c.rerouteBsId = route.firstHopIsBs ? route.firstHopBsId : c.defaultBsId;

    std::ostringstream details;
    details << "{\"reason\":\"" << reason << "\",\"engine\":\"BSBSSP\",\"path\":\""
            << route.pathDesc << "\",\"cost\":" << std::fixed << std::setprecision(3) << route.totalCost << "}";

    AddEvent(now,
             "ROUTE_COMPUTE",
             "INFO",
             static_cast<int>(clusterId),
             static_cast<int>(c.currentChNodeId),
             "BSBSSP reroute computed",
             details.str());
    return true;
}

static void BuildScenarioFromMap(const std::filesystem::path& mapDir)
{
    gNodes = LoadNodesCsv(mapDir / "nodes.csv");
    gBsRows.clear();
    gChRows = LoadChBsCsv(mapDir / "ch_bs.csv", gBsRows);
    auto nodeClusterPairs = LoadNodeClusterMap(mapDir / "node_cluster_map.csv");

    gNodeToCluster.assign(gNodes.size(), 0);

    std::map<uint32_t, uint32_t> nodeToCh;
    std::map<uint32_t, std::vector<uint32_t>> clusterMembers;
    std::map<uint32_t, uint32_t> clusterChNode;
    for (const auto& ch : gChRows)
    {
        clusterChNode[ch.chId] = ch.nodeId;
    }
    for (const auto& p : nodeClusterPairs)
    {
        const uint32_t nodeId = p.first;
        const uint32_t clusterId = p.second;
        gNodeToCluster[nodeId] = clusterId;
        if (clusterChNode.count(clusterId) && clusterChNode[clusterId] == nodeId)
        {
            continue;
        }
        clusterMembers[clusterId].push_back(nodeId);
    }

    gClusters.clear();
    gClusters.resize(gChRows.size());
    for (const auto& ch : gChRows)
    {
        auto& c = gClusters[ch.chId];
        c.clusterId = ch.chId;
        c.chNodeId = ch.nodeId;
        c.currentChNodeId = ch.nodeId;
        c.defaultBsId = FindNearestBs(ch.x, ch.y);
        c.rerouteBsId = c.defaultBsId;
        c.members = clusterMembers[ch.chId];
        std::sort(c.members.begin(), c.members.end());
    }

    gResidualJ.assign(gNodes.size(), 2.0);
    gConsumedJ.assign(gNodes.size(), 0.0);
    gNodeToCluster.assign(gNodes.size(), 0);
    for (const auto& p : nodeClusterPairs)
    {
        gNodeToCluster[p.first] = p.second;
    }
    for (const auto& ch : gChRows)
    {
        gNodeToCluster[ch.nodeId] = ch.chId;
    }

    // Runtime deterministic choices.
    gState.clusterCount = static_cast<uint32_t>(gClusters.size());
    gState.bsCount = static_cast<uint32_t>(gBsRows.size());
    gState.nodeCount = static_cast<uint32_t>(gNodes.size());
    gState.areaWidth = kScaleRules.at(gState.scale).widthM;
    gState.areaHeight = kScaleRules.at(gState.scale).heightM;
    gState.relaySourceClusterId = gClusters.empty() ? 0 : static_cast<uint32_t>(gClusters.size() - 1);
    gState.relayViaClusterId = (gClusters.size() > 1) ? std::min<uint32_t>(1, static_cast<uint32_t>(gClusters.size() - 1)) : 0;
    if (gState.relayViaClusterId == gState.relaySourceClusterId && gClusters.size() > 2)
    {
        gState.relayViaClusterId = 1;
    }
    gState.targetClusterId = 0;
    if (gState.failureFamily == "F1")
    {
        gState.targetClusterId = gClusters.empty() ? 0 : static_cast<uint32_t>(gClusters.size() - 1);
    }
    else if (gState.failureFamily == "F2")
    {
        gState.targetClusterId = (gClusters.size() > 1) ? 1 : 0;
    }
    else if (gState.failureFamily == "F3")
    {
        gState.targetClusterId = 0;
    }
    else if (gState.failureFamily == "F4")
    {
        gState.targetClusterId = gClusters.empty() ? 0 : static_cast<uint32_t>(gClusters.size() - 1);
    }
    gState.targetRecoveryClusterId = gState.targetClusterId;
}

static std::string ClusterModeString(const ClusterDef& c)
{
    if (c.failed)
    {
        return "failed";
    }
    if (c.recovered)
    {
        if (c.clusterId == gState.relaySourceClusterId)
        {
            return "relay";
        }
        return c.loadFactor < 1.0 ? "shed" : "direct";
    }
    return (c.clusterId == gState.relaySourceClusterId) ? "relay" : "direct";
}

static std::string ClusterNextHopString(const ClusterDef& c)
{
    if (c.failed)
    {
        return "-";
    }
    if (IsArchitectureB() && c.rerouteActive)
    {
        if (c.rerouteViaClusterId != kInvalidId && c.rerouteViaClusterId < gClusters.size())
        {
            return std::string("CH") + std::to_string(gClusters[c.rerouteViaClusterId].currentChNodeId);
        }
        const uint32_t bsId = (c.rerouteBsId == kInvalidId) ? c.defaultBsId : c.rerouteBsId;
        return std::string("BS") + std::to_string(bsId);
    }
    if (c.clusterId == gState.relaySourceClusterId)
    {
        const auto& relay = gClusters[gState.relayViaClusterId];
        return std::string("CH") + std::to_string(relay.currentChNodeId);
    }
    if (c.recovered && gState.healingId == "H2")
    {
        return std::string("BS") + std::to_string(c.defaultBsId);
    }
    return std::string("BS") + std::to_string(c.defaultBsId);
}

static void RecordSnapshot(double simTime)
{
    uint64_t pendingRawTotal = 0;
    for (const auto& c : gClusters)
    {
        pendingRawTotal += c.pendingRaw;
    }

    double avg = 0.0;
    double minv = std::numeric_limits<double>::max();
    uint32_t lowNodes = 0;
    for (double e : gResidualJ)
    {
        avg += e;
        minv = std::min(minv, e);
        if (e <= LowEnergyThresholdJ())
        {
            ++lowNodes;
        }
    }
    if (!gResidualJ.empty())
    {
        avg /= static_cast<double>(gResidualJ.size());
    }
    if (minv == std::numeric_limits<double>::max())
    {
        minv = 0.0;
    }
    const double consumed = std::accumulate(gConsumedJ.begin(), gConsumedJ.end(), 0.0);

    uint32_t failedChs = 0;
    uint32_t recoveredClusters = 0;
    for (const auto& c : gClusters)
    {
        if (c.failed)
        {
            ++failedChs;
        }
        if (c.recovered)
        {
            ++recoveredClusters;
        }
        double memberResidualSum = 0.0;
        double clusterConsumed = gConsumedJ[c.currentChNodeId];
        for (uint32_t memberId : c.members)
        {
            memberResidualSum += gResidualJ[memberId];
            clusterConsumed += gConsumedJ[memberId];
        }
        gClusterSnapshots.push_back({simTime,
                                     c.clusterId,
                                     c.chNodeId,
                                     c.currentChNodeId,
                                     c.failed ? "failed" : (c.recovered ? "recovered" : "normal"),
                                     ClusterModeString(c),
                                     ClusterNextHopString(c),
                                     static_cast<uint32_t>(c.members.size()),
                                     c.rawRx,
                                     c.pendingRaw,
                                     c.aggTx,
                                     c.relayFwd,
                                     gResidualJ[c.currentChNodeId],
                                     c.members.empty() ? 0.0 : memberResidualSum / static_cast<double>(c.members.size()),
                                     clusterConsumed});
    }

    if (gState.firstRecoveredAggregateS < 0.0 && recoveredClusters > 0)
    {
        gState.firstRecoveredAggregateS = simTime;
    }

    gGlobalSnapshots.push_back({simTime,
                                gGlobalRawTx,
                                gGlobalRawRx,
                                gGlobalAggTx,
                                gGlobalAggRx,
                                gGlobalDirectAggRx,
                                gGlobalRelayedAggRx,
                                gGlobalRelayFwd,
                                lowNodes,
                                failedChs,
                                recoveredClusters,
                                pendingRawTotal,
                                avg,
                                minv,
                                consumed});
}

static void TrafficTick()
{
    const double simTime = Simulator::Now().GetSeconds();
    const bool inTrafficWindow = simTime <= std::max(0.0, gState.simTime - 6.0);
    if (inTrafficWindow)
    {
        for (auto& c : gClusters)
        {
            if (c.failed)
            {
                continue;
            }
            const bool shed = c.recovered && gState.healingId == "H3";
            for (size_t i = 0; i < c.members.size(); ++i)
            {
                const uint32_t memberId = c.members[i];
                if (shed && (i % 2 == 1))
                {
                    continue;
                }
                const double linkScale = c.linkQuality;
                const double loadScale = c.loadFactor;
                const bool overloaded = c.overloaded && (c.pendingRaw > 3);
                if (overloaded)
                {
                    ++gClusters[c.clusterId].dropped;
                    AddEvent(simTime, "OVERFLOW", "WARN", static_cast<int>(c.clusterId), static_cast<int>(memberId), "queue overflow drop");
                    continue;
                }
                gGlobalRawTx++;
                gClusters[c.clusterId].rawTx++;
                gClusters[c.clusterId].pendingRaw++;
                const auto& memberNode = gNodes[memberId];
                const auto& chNode = gNodes[c.currentChNodeId];

                const double memberDistance =
                    DistanceM(memberNode.x,
                            memberNode.y,
                            chNode.x,
                            chNode.y);

                ApplyEnergy(memberId,
                            MemberTxEnergy(memberDistance) *
                            gState.loadMultiplier);
                if (gResidualJ[memberId] <= LowEnergyThresholdJ())
                {
                    AddEvent(simTime, "INIT", "INFO", static_cast<int>(c.clusterId), static_cast<int>(memberId), "low-energy node observed");
                }
                if (linkScale < 1.0 && ((gGlobalRawTx + memberId) % 5 == 0))
                {
                    ++gClusters[c.clusterId].dropped;
                    AddEvent(simTime, "DEGRADE", "WARN", static_cast<int>(c.clusterId), static_cast<int>(memberId), "degraded link drop", "{\"family\":\"F2\"}");
                    continue;
                }
                (void)loadScale;
                gClusters[c.clusterId].rawRx++;
                gGlobalRawRx++;
                ApplyEnergy(c.currentChNodeId,
                            ChRxEnergy(memberDistance));
                if (gResidualJ[c.currentChNodeId] <= 0.7 && !c.failed && gState.failureFamily == "F1")
                {
                    AddEvent(simTime, "FAILURE", "WARN", static_cast<int>(c.clusterId), static_cast<int>(c.currentChNodeId), "CH low-energy warning");
                }
            }
        }
    }
    Simulator::Schedule(Seconds(gState.trafficInterval), &TrafficTick);
}

static void AggregateTick()
{
    const double simTime = Simulator::Now().GetSeconds();
    for (auto& c : gClusters)
    {
        if (c.failed)
        {
            continue;
        }
        if (c.pendingRaw == 0)
        {
            continue;
        }
        const uint32_t chId = c.currentChNodeId;
        const uint32_t pending = c.pendingRaw;
        c.pendingRaw = 0;
        c.aggTx++;
        gGlobalAggTx++;
        gGlobalAggRx++;
        ApplyEnergy(chId, 0.0002 * pending);
        const auto& chNode = gNodes[chId];

        uint32_t bsId = c.defaultBsId;

        double bsX = 0.0;
        double bsY = 0.0;

        for (const auto& bs : gBsRows)
        {
            if (bs.bsId == bsId)
            {
                bsX = bs.x;
                bsY = bs.y;
                break;
            }
        }

        const double chBsDistance =
            DistanceM(
                chNode.x,
                chNode.y,
                bsX,
                bsY);

        ApplyEnergy(
            chId,
            ChToBsTxEnergy(chBsDistance));

        const bool useRelay = (c.clusterId == gState.relaySourceClusterId && !c.failed && !c.overloaded);
        if (useRelay)
        {
            gGlobalRelayedAggRx++;
            gGlobalRelayFwd++;
            c.relayFwd++;
            if (!gClusters[gState.relayViaClusterId].failed)
            {
                ApplyEnergy(gClusters[gState.relayViaClusterId].currentChNodeId, 0.0006);
                ApplyEnergy(gClusters[gState.relayViaClusterId].currentChNodeId, 0.0012);
            }
            if (gState.failureFamily == "F4" && c.recovered)
            {
                c.overloaded = true;
                AddEvent(simTime, "RELAY_OVERLOAD", "WARN", static_cast<int>(c.clusterId), static_cast<int>(chId), "relay path overload after healing");
            }
        }
        else
        {
            gGlobalDirectAggRx++;
        }
        AddEvent(simTime, "AGGREGATE", "INFO", static_cast<int>(c.clusterId), static_cast<int>(chId), "aggregate sent", std::string("{\"pending_raw\":") + std::to_string(pending) + "}");
    }
    Simulator::Schedule(Seconds(gState.aggregationInterval), &AggregateTick);
}

static void RecoveryTick();

static void FailureTick()
{
    if (!gState.enableFailure || gState.variant == "V1")
    {
        return;
    }
    auto& c = gClusters[gState.targetClusterId];
    if (c.failed)
    {
        return;
    }
    c.failed = true;
    AddEvent(gState.failureTime, "FAILURE", "WARN", static_cast<int>(c.clusterId), static_cast<int>(c.currentChNodeId), "failure injected", std::string("{\"family\":\"") + gState.failureFamily + "\"}");
    if (gState.failureFamily == "F1")
    {
        gResidualJ[c.currentChNodeId] = 0.0;
        AddEvent(gState.failureTime, "FAILURE", "WARN", static_cast<int>(c.clusterId), static_cast<int>(c.currentChNodeId), "CH energy depletion");
    }
    else if (gState.failureFamily == "F2")
    {
        c.linkQuality = 0.25;
        AddEvent(gState.failureTime, "DEGRADE", "WARN", static_cast<int>(c.clusterId), static_cast<int>(c.currentChNodeId), "progressive link degradation started");
    }
    else if (gState.failureFamily == "F3")
    {
        c.overloaded = true;
        AddEvent(gState.failureTime, "OVERFLOW", "WARN", static_cast<int>(c.clusterId), static_cast<int>(c.currentChNodeId), "queue overload started");
    }
    else if (gState.failureFamily == "F4")
    {
        c.overloaded = false;
        AddEvent(gState.failureTime, "RELAY", "INFO", static_cast<int>(c.clusterId), static_cast<int>(c.currentChNodeId), "relay overload precursor active");
    }

    if (gState.enableRecovery && gState.variant == "V3" && !gState.recoveryScheduled)
    {
        if (gState.targetRecoveryClusterId >= gClusters.size())
        {
            gState.targetRecoveryClusterId = c.clusterId;
        }
        const auto& recoveryTarget = gClusters[gState.targetRecoveryClusterId];
        gState.recoveryAppliedDelayS = ComputeAppliedRecoveryDelayS(recoveryTarget);
        gState.recoveryAppliedTimeS = gState.failureTime + gState.recoveryAppliedDelayS;
        gState.recoveryScheduled = true;

        Simulator::Schedule(Seconds(gState.recoveryAppliedTimeS), &RecoveryTick);

        std::ostringstream details;
        details << std::fixed << std::setprecision(3)
                << "{\"delay_s\":" << gState.recoveryAppliedDelayS
                << ",\"applied_s\":" << gState.recoveryAppliedTimeS
                << ",\"stress\":" << gState.recoveryStressScore
                << ",\"queue_norm\":" << gState.recoveryQueueNorm
                << ",\"cluster_norm\":" << gState.recoveryClusterNorm
                << ",\"energy_norm\":" << gState.recoveryEnergyNorm
                << ",\"distance_norm\":" << gState.recoveryDistanceNorm
                << "}";
        AddEvent(gState.failureTime,
                 "RECOVERY_PLAN",
                 "INFO",
                 static_cast<int>(recoveryTarget.clusterId),
                 static_cast<int>(recoveryTarget.currentChNodeId),
                 "dynamic recovery scheduled",
                 details.str());
    }
}

static uint32_t PickReplacementCh(uint32_t clusterId)
{
    const auto& c = gClusters[clusterId];
    uint32_t bestNode = c.currentChNodeId;
    double bestEnergy = -1.0;
    for (uint32_t memberId : c.members)
    {
        if (gResidualJ[memberId] > bestEnergy)
        {
            bestEnergy = gResidualJ[memberId];
            bestNode = memberId;
        }
    }
    return bestNode;
}

static void RecoveryTick()
{
    if (!gState.enableRecovery || gState.variant != "V3")
    {
        return;
    }
    auto& c = gClusters[gState.targetRecoveryClusterId];
    if (c.recovered)
    {
        return;
    }
    const double recoveryEventTime = Simulator::Now().GetSeconds();
    gState.recoveryEventTimeS = recoveryEventTime;
    const uint32_t replacement = PickReplacementCh(c.clusterId);
    if (gState.healingId == "H1")
    {
        c.currentChNodeId = replacement;
        c.recovered = true;
        AddEvent(recoveryEventTime, "RECOVERY", "INFO", static_cast<int>(c.clusterId), static_cast<int>(replacement), "CH handover applied");
    }
    else if (gState.healingId == "H2")
    {
        c.recovered = true;
        c.linkQuality = 1.0;
        AddEvent(recoveryEventTime, "RECOVERY", "INFO", static_cast<int>(c.clusterId), static_cast<int>(c.currentChNodeId), "route switch / parent change applied");
    }
    else if (gState.healingId == "H3")
    {
        c.currentChNodeId = replacement;
        c.recovered = true;
        c.loadFactor = 0.5;
        AddEvent(recoveryEventTime, "RECOVERY", "INFO", static_cast<int>(c.clusterId), static_cast<int>(replacement), "load shedding applied");
    }
    else if (gState.healingId == "H4")
    {
        c.currentChNodeId = replacement;
        c.recovered = true;
        c.loadFactor = 0.75;
        if (c.clusterId == gState.relaySourceClusterId)
        {
            gClusters[gState.relayViaClusterId].overloaded = true;
        }
        AddEvent(recoveryEventTime, "RECOVERY", "INFO", static_cast<int>(c.clusterId), static_cast<int>(replacement), "recovery rebalancing applied");
    }
    c.failed = false;
    c.linkQuality = 1.0;

    if (IsArchitectureB())
    {
        ApplyBsbsspRoute(c.clusterId, "recovery", false);
        if (gState.healingId == "H4" && c.clusterId == gState.relaySourceClusterId)
        {
            ApplyBsbsspRoute(gState.relayViaClusterId, "relay_balance", false);
        }
    }
}

static void DashboardTick()
{
    RecordSnapshot(Simulator::Now().GetSeconds());
    Simulator::Schedule(Seconds(gState.dashboardInterval), &DashboardTick);
}

static std::string BuildExternalRunId()
{
    std::ostringstream os;
    os << gState.runSpecId << "_" << std::time(nullptr);
    return os.str();
}

static std::filesystem::path EnsureRunDir()
{
    const std::string label = gState.exportRunLabel.empty() ? (std::string("run_") + BuildExternalRunId()) : gState.exportRunLabel;
    const std::filesystem::path root(gState.exportRootDir);
    std::filesystem::create_directories(root);
    const std::filesystem::path runDir = root / label;
    std::filesystem::create_directories(runDir);
    return runDir;
}

static void ExportFiles(const std::filesystem::path& runDir)
{
    const std::string externalRunId = runDir.filename().string().rfind("run_", 0) == 0 ? runDir.filename().string().substr(4) : runDir.filename().string();

    {
        std::ofstream meta(runDir / "run_meta.json");
        meta << "{\n";
        meta << "  \"external_run_id\": \"" << JsonEscape(externalRunId) << "\",\n";
        meta << "  \"schema_version\": \"m1_v1\",\n";
        meta << "  \"scenario_name\": \"m3-scenario-library\",\n";
        meta << "  \"scenario_type\": \"wsn-self-healing\",\n";
        meta << "  \"sim_time_s\": " << std::fixed << std::setprecision(3) << gState.simTime << ",\n";
        meta << "  \"node_count\": " << gState.nodeCount << ",\n";
        meta << "  \"cluster_count\": " << gState.clusterCount << ",\n";
        meta << "  \"traffic_interval_s\": " << gState.trafficInterval << ",\n";
        meta << "  \"aggregation_interval_s\": " << gState.aggregationInterval << ",\n";
        meta << "  \"failure_time_s\": " << gState.failureTime << ",\n";
        meta << "  \"recovery_delay_s\": " << gState.recoveryDelay << ",\n";
        meta << "  \"recovery_nominal_delay_s\": " << gState.recoveryDelay << ",\n";
        meta << "  \"recovery_applied_delay_s\": " << gState.recoveryAppliedDelayS << ",\n";
        meta << "  \"recovery_applied_s\": " << gState.recoveryAppliedTimeS << ",\n";
        meta << "  \"recovery_event_time_s\": " << gState.recoveryEventTimeS << ",\n";
        meta << "  \"recovery_scheduled\": " << (gState.recoveryScheduled ? "true" : "false") << ",\n";
        meta << "  \"recovery_stress_score\": " << gState.recoveryStressScore << ",\n";
        meta << "  \"recovery_map_profile_penalty_s\": " << gState.recoveryMapProfilePenaltyS << ",\n";
        meta << "  \"recovery_queue_norm\": " << gState.recoveryQueueNorm << ",\n";
        meta << "  \"recovery_cluster_norm\": " << gState.recoveryClusterNorm << ",\n";
        meta << "  \"recovery_energy_norm\": " << gState.recoveryEnergyNorm << ",\n";
        meta << "  \"recovery_distance_norm\": " << gState.recoveryDistanceNorm << ",\n";
        meta << "  \"recovery_enabled\": " << (gState.enableRecovery ? "true" : "false") << ",\n";
        meta << "  \"dashboard_interval_s\": " << gState.dashboardInterval << ",\n";
        meta << "  \"run_spec_id\": \"" << JsonEscape(gState.runSpecId) << "\",\n";
        meta << "  \"map_id\": \"" << JsonEscape(gState.mapId) << "\",\n";
        meta << "  \"map_signature\": \"" << JsonEscape(gState.mapSignature) << "\",\n";
        meta << "  \"architecture\": \"" << JsonEscape(gState.architecture) << "\",\n";
        meta << "  \"routing_engine\": \"" << (IsArchitectureB() ? "bsbssp_v1_approx" : "baseline") << "\",\n";
        meta << "  \"variant\": \"" << JsonEscape(gState.variant) << "\",\n";
        meta << "  \"failure_family\": \"" << JsonEscape(gState.failureFamily) << "\",\n";
        meta << "  \"healing_id\": \"" << JsonEscape(gState.healingId) << "\",\n";
        meta << "  \"load\": \"" << JsonEscape(gState.load) << "\",\n";
        meta << "  \"scale\": \"" << JsonEscape(gState.scale) << "\",\n";
        meta << "  \"seed\": " << gState.seed << ",\n";
        meta << "  \"source_file\": \"" << JsonEscape(gState.simSource) << "\"\n";
        meta << "}\n";
    }

    {
        std::ofstream nodes(runDir / "nodes_static.csv");
        nodes << "external_run_id,node_id,role,original_cluster_id,original_ch_id,initial_energy_j,x,y,z\n";
        for (const auto& n : gNodes)
        {
            const uint32_t clusterId = gNodeToCluster[n.nodeId];
            const bool isCh = gClusters[clusterId].chNodeId == n.nodeId;
            nodes << externalRunId << "," << n.nodeId << "," << (isCh ? "ch" : "member") << "," << clusterId << "," << gClusters[clusterId].chNodeId << ",2.000000," << std::fixed << std::setprecision(3) << n.x << "," << n.y << ",0.000\n";
        }
        for (const auto& bs : gBsRows)
        {
            nodes << externalRunId << "," << (gState.nodeCount + bs.bsId) << ",bs,,," << "0.000000," << std::fixed << std::setprecision(3) << bs.x << "," << bs.y << ",0.000\n";
        }
    }

    {
        std::ofstream global(runDir / "global_timeseries.csv");
        global << "external_run_id,sim_time,raw_tx_cum,raw_rx_cum,agg_tx_cum,agg_rx_cum,direct_agg_rx_cum,relayed_agg_rx_cum,relay_fwd_cum,avg_res_j,min_res_j,consumed_j,low_nodes,failed_chs,recovered_clusters,pending_raw_total\n";
        for (const auto& s : gGlobalSnapshots)
        {
            global << externalRunId << "," << std::fixed << std::setprecision(3) << s.simTime << "," << s.rawTx << "," << s.rawRx << "," << s.aggTx << "," << s.aggRx << "," << s.directAggRx << "," << s.relayedAggRx << "," << s.relayFwd << "," << std::setprecision(6) << s.avgResJ << "," << s.minResJ << "," << s.consumedJ << "," << s.lowNodes << "," << s.failedChs << "," << s.recoveredClusters << "," << s.pendingRawTotal << "\n";
        }
    }

    {
        std::ofstream cluster(runDir / "cluster_timeseries.csv");
        cluster << "external_run_id,sim_time,cluster_id,original_ch_id,current_ch_id,status,mode,next_hop,members_count,raw_rx_cum,pending_raw,agg_tx_cum,relay_fwd_cum,ch_res_j,avg_mem_res_j,cluster_consumed_j\n";
        for (const auto& s : gClusterSnapshots)
        {
            cluster << externalRunId << "," << std::fixed << std::setprecision(3) << s.simTime << "," << s.clusterId << "," << s.originalChId << "," << s.currentChId << "," << CsvEscape(s.status) << "," << CsvEscape(s.mode) << "," << CsvEscape(s.nextHop) << "," << s.membersCount << "," << s.rawRx << "," << s.pendingRaw << "," << s.aggTx << "," << s.relayFwd << "," << std::setprecision(6) << s.chResJ << "," << s.avgMemResJ << "," << s.clusterConsumedJ << "\n";
        }
    }

    {
        std::ofstream events(runDir / "events.csv");
        events << "external_run_id,sim_time,event_type,severity,cluster_id,node_id,message,details_json\n";
        for (const auto& e : gEvents)
        {
            events << externalRunId << "," << std::fixed << std::setprecision(3) << e.simTime << "," << CsvEscape(e.eventType) << "," << CsvEscape(e.severity) << ",";
            if (e.clusterId >= 0)
            {
                events << e.clusterId;
            }
            events << ",";
            if (e.nodeId >= 0)
            {
                events << e.nodeId;
            }
            events << "," << CsvEscape(e.message) << "," << CsvEscape(e.detailsJson) << "\n";
        }
    }

    {
        std::ofstream summary(runDir / "run_summary.json");
        const auto& last = gGlobalSnapshots.empty() ? GlobalSnapshot{} : gGlobalSnapshots.back();
        const double trafficRecoveryDelay = (gState.firstRecoveredAggregateS >= 0.0)
                                                ? (gState.firstRecoveredAggregateS - gState.failureTime)
                                                : -1.0;
        summary << "{\n";
        summary << "  \"external_run_id\": \"" << JsonEscape(externalRunId) << "\",\n";
        summary << "  \"final_sim_time\": " << std::fixed << std::setprecision(3) << Simulator::Now().GetSeconds() << ",\n";
        summary << "  \"raw_tx_cum\": " << last.rawTx << ",\n";
        summary << "  \"raw_rx_cum\": " << last.rawRx << ",\n";
        summary << "  \"agg_tx_cum\": " << last.aggTx << ",\n";
        summary << "  \"agg_rx_cum\": " << last.aggRx << ",\n";
        summary << "  \"direct_agg_rx_cum\": " << last.directAggRx << ",\n";
        summary << "  \"relayed_agg_rx_cum\": " << last.relayedAggRx << ",\n";
        summary << "  \"relay_fwd_cum\": " << last.relayFwd << ",\n";
        summary << "  \"failed_chs\": " << last.failedChs << ",\n";
        summary << "  \"recovered_clusters\": " << last.recoveredClusters << ",\n";
        summary << "  \"avg_res_j\": " << std::setprecision(6) << last.avgResJ << ",\n";
        summary << "  \"min_res_j\": " << last.minResJ << ",\n";
        summary << "  \"consumed_j\": " << last.consumedJ << ",\n";
        summary << "  \"low_nodes\": " << last.lowNodes << ",\n";
        summary << "  \"pending_raw_total\": " << last.pendingRawTotal << ",\n";
        summary << "  \"failure_time_s\": " << gState.failureTime << ",\n";
        summary << "  \"recovery_applied_delay_s\": " << gState.recoveryAppliedDelayS << ",\n";
        summary << "  \"recovery_applied_s\": " << gState.recoveryAppliedTimeS << ",\n";
        summary << "  \"recovery_event_time_s\": " << gState.recoveryEventTimeS << ",\n";
        summary << "  \"first_recovered_aggregate_s\": " << gState.firstRecoveredAggregateS << ",\n";
        summary << "  \"recovery_map_profile_penalty_s\": " << gState.recoveryMapProfilePenaltyS << ",\n";
        summary << "  \"traffic_recovery_delay_s\": " << trafficRecoveryDelay << "\n";
        summary << "}\n";
    }

    {
        std::ofstream nodesFinal(runDir / "node_final_summary.csv");
        nodesFinal << "external_run_id,node_id,role,cluster_id,residual_j,consumed_j,final_status\n";
        for (const auto& n : gNodes)
        {
            const uint32_t clusterId = gNodeToCluster[n.nodeId];
            const bool isCh = gClusters[clusterId].chNodeId == n.nodeId;
            std::string status = "normal";
            if (gClusters[clusterId].failed && isCh)
            {
                status = "failed";
            }
            else if (gResidualJ[n.nodeId] <= LowEnergyThresholdJ())
            {
                status = "low_energy";
            }
            nodesFinal << externalRunId << "," << n.nodeId << "," << (isCh ? "ch" : "member") << "," << clusterId << "," << std::fixed << std::setprecision(6) << gResidualJ[n.nodeId] << "," << gConsumedJ[n.nodeId] << "," << status << "\n";
        }
        for (const auto& bs : gBsRows)
        {
            nodesFinal << externalRunId << "," << (gState.nodeCount + bs.bsId) << ",bs,,0.000000,0.000000,n/a\n";
        }
    }

    std::cout << "[Export] Run artifacts written to: " << runDir.string() << "\n";
}

} // namespace

int main(int argc, char* argv[])
{
    CommandLine cmd(__FILE__);
    std::string mapDir;
    cmd.AddValue("runSpecId", "M1 run-spec id", gState.runSpecId);
    cmd.AddValue("mapId", "M2 map id", gState.mapId);
    cmd.AddValue("mapSignature", "M2 map signature", gState.mapSignature);
    cmd.AddValue("mapDir", "Path to map package directory", mapDir);
    cmd.AddValue("architecture", "Architecture label", gState.architecture);
    cmd.AddValue("variant", "Scenario variant", gState.variant);
    cmd.AddValue("failureFamily", "Failure family", gState.failureFamily);
    cmd.AddValue("healingId", "Healing id", gState.healingId);
    cmd.AddValue("load", "Load tier", gState.load);
    cmd.AddValue("scale", "Scale id", gState.scale);
    cmd.AddValue("seed", "Seed value", gState.seed);
    cmd.AddValue("simTime", "Simulation time", gState.simTime);
    cmd.AddValue("trafficInterval", "Traffic interval", gState.trafficInterval);
    cmd.AddValue("aggregationInterval", "Aggregation interval", gState.aggregationInterval);
    cmd.AddValue("dashboardInterval", "Dashboard interval", gState.dashboardInterval);
    cmd.AddValue("failureTime", "Failure onset time", gState.failureTime);
    cmd.AddValue("recoveryDelay", "Recovery delay", gState.recoveryDelay);
    cmd.AddValue("enableFailure", "Enable failure injection", gState.enableFailure);
    cmd.AddValue("enableRecovery", "Enable healing", gState.enableRecovery);
    cmd.AddValue("enableRunExport", "Enable standard run export", gState.enableRunExport);
    cmd.AddValue("exportRootDir", "Export root directory", gState.exportRootDir);
    cmd.AddValue("exportRunLabel", "Explicit run export label", gState.exportRunLabel);
    cmd.AddValue("loadMultiplier", "Traffic multiplier", gState.loadMultiplier);
    cmd.Parse(argc, argv);

    if (gState.architecture.empty())
    {
        gState.architecture = "A";
    }
    if (gState.architecture != "A" && gState.architecture != "B")
    {
        std::cerr << "Architecture must be A or B.\n";
        return 2;
    }

    if (mapDir.empty())
    {
        std::cerr << "Missing --mapDir\n";
        return 2;
    }

    if (gState.seed == 0)
    {
        gState.seed = 1;
    }
    gState.targetRecoveryClusterId = 0;

    const auto& rule = kScaleRules.at(gState.scale);
    BuildScenarioFromMap(std::filesystem::path(mapDir));
    if (gNodes.size() != rule.nodeCount || gClusters.size() != rule.chCount || gBsRows.size() != rule.bsCount)
    {
        std::cerr << "Map package does not match frozen scale rules.\n";
        return 3;
    }

    gState.nodeCount = static_cast<uint32_t>(gNodes.size());
    gState.clusterCount = static_cast<uint32_t>(gClusters.size());
    gState.bsCount = static_cast<uint32_t>(gBsRows.size());
    gState.exportRunLabel = gState.exportRunLabel.empty() ? std::string("run_") + gState.runSpecId + "_" + std::to_string(gState.seed) : gState.exportRunLabel;

    if (IsArchitectureB() && gState.enableRecovery && gState.variant == "V3")
    {
        const auto precheck = ComputeBsbsspRoute(gState.targetRecoveryClusterId);
        if (!precheck.reachable)
        {
            std::cerr << "Invalid Architecture B path: no feasible BSBSSP route for target cluster.\n";
            return 4;
        }
    }

    AddEvent(0.0,
             "INIT",
             "INFO",
             -1,
             -1,
             "simulation initialized",
             std::string("{\"run_spec_id\":\"") + JsonEscape(gState.runSpecId) + "\",\"architecture\":\"" + JsonEscape(gState.architecture) + "\"}");
    RecordSnapshot(0.0);

    Simulator::Schedule(Seconds(gState.trafficInterval), &TrafficTick);
    Simulator::Schedule(Seconds(gState.aggregationInterval), &AggregateTick);
    if (gState.enableFailure && gState.variant != "V1")
    {
        Simulator::Schedule(Seconds(gState.failureTime), &FailureTick);
    }
    Simulator::Schedule(Seconds(gState.dashboardInterval), &DashboardTick);

    Simulator::Stop(Seconds(gState.simTime));
    Simulator::Run();
    RecordSnapshot(Simulator::Now().GetSeconds());

    const auto runDir = gState.enableRunExport ? EnsureRunDir() : std::filesystem::path{};
    if (gState.enableRunExport)
    {
        ExportFiles(runDir);
    }

    std::cout << "\nSimulation finished at t=" << std::fixed << std::setprecision(3) << Simulator::Now().GetSeconds() << "s\n";
    Simulator::Destroy();
    return 0;
}
