#include "ns3/core-module.h"
#include "ns3/internet-module.h"
#include "ns3/mobility-module.h"
#include "ns3/netanim-module.h"
#include "ns3/network-module.h"
#include "ns3/wifi-module.h"

#include <array>
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <cstdint>
#include <ctime>
#include <deque>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <memory>
#include <chrono>
#include <sstream>
#include <string>
#include <thread>
#include <vector>
#include <unistd.h>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("ClusterDashboardM1");

namespace
{

constexpr uint32_t kClusters = 3;
constexpr uint32_t kNodesPerCluster = 6; // includes CH
constexpr uint32_t kSensorCount = kClusters * kNodesPerCluster;
constexpr uint32_t kBaseStationId = kSensorCount;
constexpr uint16_t kChPort = 7000;
constexpr uint16_t kBsPort = 7001;

constexpr uint32_t kRelaySourceCluster = 2;
constexpr uint32_t kRelayViaCluster = 1;

class AggregateMetaHeader : public Header
{
  public:
    static TypeId
    GetTypeId()
    {
        static TypeId tid = TypeId("ns3::AggregateMetaHeader")
                                .SetParent<Header>()
                                .AddConstructor<AggregateMetaHeader>();
        return tid;
    }

    TypeId
    GetInstanceTypeId() const override
    {
        return GetTypeId();
    }

    uint32_t
    GetSerializedSize() const override
    {
        return 3;
    }

    void
    Serialize(Buffer::Iterator start) const override
    {
        start.WriteU8(static_cast<uint8_t>(m_originClusterId));
        start.WriteU8(static_cast<uint8_t>(m_originChId));
        start.WriteU8(static_cast<uint8_t>(m_relayed ? 1 : 0));
    }

    uint32_t
    Deserialize(Buffer::Iterator start) override
    {
        m_originClusterId = start.ReadU8();
        m_originChId = start.ReadU8();
        m_relayed = (start.ReadU8() != 0);
        return GetSerializedSize();
    }

    void
    Print(std::ostream& os) const override
    {
        os << "originCluster=" << static_cast<uint32_t>(m_originClusterId)
           << " originCh=" << static_cast<uint32_t>(m_originChId)
           << " relayed=" << (m_relayed ? 1 : 0);
    }

    void SetOriginClusterId(uint8_t v) { m_originClusterId = v; }
    void SetOriginChId(uint8_t v) { m_originChId = v; }
    void SetRelayed(bool v) { m_relayed = v; }
    uint8_t GetOriginClusterId() const { return m_originClusterId; }
    uint8_t GetOriginChId() const { return m_originChId; }
    bool GetRelayed() const { return m_relayed; }

  private:
    uint8_t m_originClusterId = 0;
    uint8_t m_originChId = 0;
    bool m_relayed = false;
};

struct ClusterDef
{
    uint32_t clusterId;
    uint32_t chId;
    std::vector<uint32_t> members;
};

struct ClusterCounters
{
    uint64_t rawTxToCh = 0;
    uint64_t rawRxAtCh = 0;
    uint64_t pendingRaw = 0;
    uint64_t aggTxToBs = 0;
    uint64_t relayForwardCount = 0;
    uint64_t relayRxCount = 0;
    double lastRxTimeSec = -1.0;
    double lastAggTimeSec = -1.0;
    double lastAggDeliveredTimeSec = -1.0;
    bool firstAggCreated = false;
    bool firstAggDelivered = false;
    bool firstRelayAggCreated = false;
    bool firstRelayAggReceived = false;
    bool firstRelayForwarded = false;
    bool firstRelayDelivered = false;
};

enum class ClusterHealth : uint8_t
{
    NORMAL = 0,
    FAILED = 1,
    RECOVERING = 2,
    RECOVERED = 3,
};

struct EnergySnapshot
{
    double avgResidualJ = 0.0;
    double minResidualJ = 0.0;
    double totalConsumedJ = 0.0;
    uint32_t lowEnergyNodes = 0;
};

NodeContainer gSensorNodes;
Ptr<Node> gBaseStation;
Ipv4InterfaceContainer gIfaces;

std::array<ClusterDef, kClusters> gClusterDefs;
std::array<ClusterCounters, kClusters> gClusterCounters;
std::array<ClusterHealth, kClusters> gClusterHealth{};
std::array<uint32_t, kClusters> gClusterCurrentCh{};
std::array<uint32_t, kSensorCount> gSensorToCluster{};
std::array<bool, kSensorCount> gFirstTxSeen{};
std::array<bool, kSensorCount> gLowEnergyAlerted{};
std::array<bool, kClusters> gChLowEnergyAlerted{};
std::array<bool, kSensorCount> gNodeFailed{};

std::array<double, kSensorCount> gResidualEnergyJ{};
std::array<double, kSensorCount> gConsumedEnergyJ{};

std::map<uint32_t, Ptr<Socket>> gMemberSockets;
std::map<uint32_t, Ptr<Socket>> gChSockets;
std::map<uint32_t, Ptr<Socket>> gChToBsSockets;
Ptr<Socket> gBsRxSocket;

std::deque<std::string> gRecentEvents;
uint64_t gGlobalRawTx = 0;
uint64_t gGlobalRawRx = 0;
uint64_t gGlobalAggTx = 0;
uint64_t gGlobalAggRx = 0;
uint64_t gGlobalDirectAggRx = 0;
uint64_t gGlobalRelayedAggRx = 0;
uint64_t gGlobalRelayForward = 0;
uint32_t gGlobalFailedChCount = 0;
uint32_t gGlobalRecoveredClusterCount = 0;

double gSimTimeSec = 30.0;
double gDashboardIntervalSec = 1.0;
double gTrafficIntervalSec = 3.0;
double gAggregationIntervalSec = 6.0;
uint32_t gPayloadBytes = 48;
uint32_t gAggregatePayloadBytes = 40;
double gMaxRangeMeters = 95.0;
bool gRealtime = true;

bool gEnableNetAnim = false;
std::string gNetAnimFile = "cluster-dashboard-m1.xml";
bool gNetAnimPacketMetadata = true;
uint32_t gNetAnimMaxPktsPerTraceFile = 500000;
double gNetAnimPollIntervalSec = 0.25;
double gHighlightWindowStartSec = 13.0;
double gHighlightWindowEndSec = 16.0;
double gHighlightSlowdownFactor = 4.0;
bool gHighlightReduceTraffic = false;
double gHighlightTrafficMultiplier = 3.0;

AnimationInterface* gAnim = nullptr;

double gInitialEnergyJ = 2.0;
double gMemberRawTxEnergyJ = 0.0008;
double gChRawRxEnergyJ = 0.0005;
double gChAggregationEnergyPerRawJ = 0.0002;
double gChAggTxEnergyJ = 0.0012;
double gRelayAggRxEnergyJ = 0.0006;
double gRelayForwardTxEnergyJ = 0.0012;
bool gEnableIdleDrain = true;
double gIdleDrainPerSecondJ = 0.00002;
double gLowEnergyThresholdPct = 25.0;
double gLowEnergyFrac = 0.25;

double gTrafficStopLeadSec = 6.0;
double gTrafficStopTimeSec = 0.0;

bool gColorEnabled = true;
bool gNoColor = false;
std::string gDashboardStyle = "combined";
uint32_t gTopK = 10;
uint32_t gEventsWindow = 8;
std::string gExportNodeEnergyCsv = "";
std::string gExportEventsCsv = "";
std::string gEnergyCsv = "";

bool gEnableRunExport = true;
std::string gExportRootDir = "outputs";
std::string gExportRunLabel = "";
std::string gCurrentRunExternalId;
std::string gCurrentRunOutputDir;

double gFailureTimeSec = 13.0;
double gRecoveryDelaySec = 1.0;
bool gEnableRecovery = true;

constexpr uint32_t kFailureClusterId = 2;
constexpr uint32_t kFailureChId = 12;

bool gFirstRecoveredRawSeen = false;
bool gFirstRecoveredAggSent = false;

uint64_t gPrevGlobalRawRx = 0;
uint64_t gPrevGlobalAggRx = 0;

uint64_t gRawDroppedCum = 0;
std::array<uint64_t, kClusters> gClusterRawDroppedCum{};
std::array<double, kClusters> gClusterDisconnectedSeconds{};
double gLastDisconnectUpdateSec = 0.0;

struct GlobalSnapshotRow
{
    double simTimeSec = 0.0;
    uint64_t rawTxCum = 0;
    uint64_t rawRxCum = 0;
    uint64_t aggTxCum = 0;
    uint64_t aggRxCum = 0;
    uint64_t directAggRxCum = 0;
    uint64_t relayedAggRxCum = 0;
    uint64_t relayFwdCum = 0;
    double avgResJ = 0.0;
    double minResJ = 0.0;
    double consumedJ = 0.0;
    uint32_t lowNodes = 0;
    uint32_t failedChs = 0;
    uint32_t recoveredClusters = 0;
    uint64_t pendingRawTotal = 0;
};

struct ClusterSnapshotRow
{
    double simTimeSec = 0.0;
    uint32_t clusterId = 0;
    uint32_t originalChId = 0;
    uint32_t currentChId = 0;
    std::string status;
    std::string mode;
    std::string nextHop;
    uint32_t membersCount = 0;
    uint64_t rawRxCum = 0;
    uint64_t pendingRaw = 0;
    uint64_t aggTxCum = 0;
    uint64_t relayFwdCum = 0;
    double chResJ = 0.0;
    double avgMemResJ = 0.0;
    double clusterConsumedJ = 0.0;
};

struct EventExportRow
{
    double simTimeSec = 0.0;
    std::string eventType;
    std::string severity;
    int32_t clusterId = -1;
    int32_t nodeId = -1;
    std::string message;
    std::string detailsJson = "{}";
};

std::vector<GlobalSnapshotRow> gGlobalSnapshots;
std::vector<ClusterSnapshotRow> gClusterSnapshots;
std::vector<EventExportRow> gEventRows;

uint32_t GetRelayChId();
double LowEnergyThresholdJ();
void AddTaggedEvent(const std::string& tag, const std::string& msg);
bool ClusterUsesRelay(uint32_t clusterId);
std::string ClusterModeString(uint32_t clusterId);
std::string ClusterHealthString(uint32_t clusterId);
std::string ClusterNextHopString(uint32_t clusterId);
EnergySnapshot GetEnergySnapshot();
std::string CsvEscape(const std::string& value);
std::string JsonEscape(const std::string& value);
std::string BuildRunExternalId();
std::string BuildDefaultRunLabel();
void CaptureSnapshot(double simTimeSec);
void InitializeRunExport();
void ExportRunFiles();

bool
IsTerminal()
{
    return isatty(fileno(stdout)) == 1;
}

std::string
Colorize(const std::string& text, const std::string& colorCode)
{
    if (!gColorEnabled)
    {
        return text;
    }
    return colorCode + text + "\033[0m";
}

std::string
GetColorCode(const std::string& style)
{
    if (!gColorEnabled)
    {
        return "";
    }
    if (style == "NORMAL")
        return "\033[32m";  // green
    if (style == "RECOVERING")
        return "\033[33m";  // yellow
    if (style == "RECOVERED")
        return "\033[33m";  // yellow
    if (style == "FAILED")
        return "\033[31m";  // red
    if (style == "RECOVERY_BURDEN")
        return "\033[33m";  // yellow (orange fallback)
    if (style == "HEADING")
        return "\033[36m";  // cyan
    if (style == "WARNING")
        return "\033[31m";  // red
    if (style == "ARROW")
        return "\033[34m";  // blue
    return "";
}

void
PrintBox(const std::string& title, const std::vector<std::string>& lines)
{
    size_t width = title.size() + 2;
    for (const auto& line : lines)
    {
        width = std::max(width, line.size());
    }
    std::cout << "\n+" << std::string(width + 2, '-') << "+\n";
    std::cout << "| " << Colorize(title, GetColorCode("HEADING"))
              << std::string(width - title.size(), ' ') << " |\n";
    std::cout << "+" << std::string(width + 2, '-') << "+\n";
    for (const auto& line : lines)
    {
        std::cout << "| " << line << std::string(width - line.size(), ' ') << " |\n";
    }
    std::cout << "+" << std::string(width + 2, '-') << "+\n";
}

std::string
FormatClusterStatus(uint32_t clusterId)
{
    const std::string text = ClusterHealthString(clusterId);
    if (gClusterHealth[clusterId] == ClusterHealth::FAILED)
    {
        return Colorize(text, GetColorCode("FAILED"));
    }
    if (gClusterHealth[clusterId] == ClusterHealth::RECOVERING)
    {
        return Colorize(text, GetColorCode("RECOVERING"));
    }
    if (gClusterHealth[clusterId] == ClusterHealth::RECOVERED)
    {
        return Colorize(text, GetColorCode("RECOVERED"));
    }
    return Colorize(text, GetColorCode("NORMAL"));
}

std::string
FormatModeString(uint32_t clusterId)
{
    const std::string mode = ClusterModeString(clusterId);
    if (mode == "failed")
    {
        return Colorize(mode, GetColorCode("FAILED"));
    }
    if (mode == "recovering")
    {
        return Colorize(mode, GetColorCode("RECOVERING"));
    }
    return mode;
}

uint32_t
ClusterNextHopId(uint32_t clusterId)
{
    if (gClusterHealth[clusterId] == ClusterHealth::FAILED)
    {
        return std::numeric_limits<uint32_t>::max();
    }
    if (ClusterUsesRelay(clusterId))
    {
        return GetRelayChId();
    }
    return kBaseStationId;
}

std::string
FormatNextHop(uint32_t nextHopId)
{
    if (nextHopId == std::numeric_limits<uint32_t>::max())
    {
        return "-";
    }
    if (nextHopId == kBaseStationId)
    {
        std::ostringstream os;
        os << "BS(" << kBaseStationId << ")";
        return os.str();
    }
    std::ostringstream os;
    os << "CH" << nextHopId << "(" << nextHopId << ")";
    return os.str();
}

std::string
FormatLastTime(double tSec)
{
    if (tSec < 0.0)
    {
        return "-";
    }
    std::ostringstream os;
    os << std::fixed << std::setprecision(1) << tSec << "s";
    return os.str();
}

void
UpdateDisconnectedAccounting(double nowSec)
{
    if (gLastDisconnectUpdateSec <= 0.0)
    {
        gLastDisconnectUpdateSec = nowSec;
        return;
    }
    const double dt = nowSec - gLastDisconnectUpdateSec;
    if (dt <= 0.0)
    {
        return;
    }
    for (uint32_t cid = 0; cid < kClusters; ++cid)
    {
        if (gClusterHealth[cid] == ClusterHealth::FAILED || gClusterHealth[cid] == ClusterHealth::RECOVERING)
        {
            gClusterDisconnectedSeconds[cid] += dt;
        }
    }
    gLastDisconnectUpdateSec = nowSec;
}

std::string
CsvEscape(const std::string& value)
{
    bool needsQuotes = false;
    for (char ch : value)
    {
        if (ch == ',' || ch == '"' || ch == '\n' || ch == '\r')
        {
            needsQuotes = true;
            break;
        }
    }
    if (!needsQuotes)
    {
        return value;
    }

    std::string escaped = "\"";
    for (char ch : value)
    {
        if (ch == '"')
        {
            escaped += "\"\"";
        }
        else
        {
            escaped.push_back(ch);
        }
    }
    escaped += "\"";
    return escaped;
}

std::string
JsonEscape(const std::string& value)
{
    std::string out;
    out.reserve(value.size() + 8);
    for (char ch : value)
    {
        switch (ch)
        {
        case '"':
            out += "\\\"";
            break;
        case '\\':
            out += "\\\\";
            break;
        case '\n':
            out += "\\n";
            break;
        case '\r':
            out += "\\r";
            break;
        case '\t':
            out += "\\t";
            break;
        default:
            out.push_back(ch);
            break;
        }
    }
    return out;
}

std::string
BuildRunExternalId()
{
    const auto now = std::chrono::system_clock::now();
    const auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(now.time_since_epoch()) % 1000;
    const std::time_t tt = std::chrono::system_clock::to_time_t(now);
    std::tm tm{};
#ifdef _WIN32
    localtime_s(&tm, &tt);
#else
    localtime_r(&tt, &tm);
#endif

    std::ostringstream os;
    os << std::put_time(&tm, "%Y%m%d_%H%M%S") << "_" << std::setw(3) << std::setfill('0') << ms.count();
    return os.str();
}

std::string
BuildDefaultRunLabel()
{
    std::ostringstream os;
    os << "run_" << gCurrentRunExternalId;
    return os.str();
}

void
CaptureSnapshot(double simTimeSec)
{
    if (!gGlobalSnapshots.empty())
    {
        const double last = gGlobalSnapshots.back().simTimeSec;
        if (std::abs(last - simTimeSec) < 1e-9)
        {
            return;
        }
    }

    GlobalSnapshotRow global;
    global.simTimeSec = simTimeSec;
    global.rawTxCum = gGlobalRawTx;
    global.rawRxCum = gGlobalRawRx;
    global.aggTxCum = gGlobalAggTx;
    global.aggRxCum = gGlobalAggRx;
    global.directAggRxCum = gGlobalDirectAggRx;
    global.relayedAggRxCum = gGlobalRelayedAggRx;
    global.relayFwdCum = gGlobalRelayForward;
    const EnergySnapshot es = GetEnergySnapshot();
    global.avgResJ = es.avgResidualJ;
    global.minResJ = es.minResidualJ;
    global.consumedJ = es.totalConsumedJ;
    global.lowNodes = es.lowEnergyNodes;
    global.failedChs = gGlobalFailedChCount;
    global.recoveredClusters = gGlobalRecoveredClusterCount;

    uint64_t pendingTotal = 0;
    for (const auto& c : gClusterCounters)
    {
        pendingTotal += c.pendingRaw;
    }
    global.pendingRawTotal = pendingTotal;
    gGlobalSnapshots.push_back(global);

    for (const auto& def : gClusterDefs)
    {
        const auto& c = gClusterCounters[def.clusterId];
        ClusterSnapshotRow row;
        row.simTimeSec = simTimeSec;
        row.clusterId = def.clusterId;
        row.originalChId = def.chId;
        row.currentChId = gClusterCurrentCh[def.clusterId];
        row.status = ClusterHealthString(def.clusterId);
        row.mode = ClusterModeString(def.clusterId);
        row.nextHop = ClusterNextHopString(def.clusterId);
        row.membersCount = static_cast<uint32_t>(def.members.size());
        row.rawRxCum = c.rawRxAtCh;
        row.pendingRaw = c.pendingRaw;
        row.aggTxCum = c.aggTxToBs;
        row.relayFwdCum = c.relayForwardCount;
        row.chResJ = gResidualEnergyJ[row.currentChId];

        double memberResidualSum = 0.0;
        double clusterConsumed = gConsumedEnergyJ[def.chId];
        for (uint32_t memberId : def.members)
        {
            memberResidualSum += gResidualEnergyJ[memberId];
            clusterConsumed += gConsumedEnergyJ[memberId];
        }
        row.avgMemResJ = def.members.empty() ? 0.0 : memberResidualSum / static_cast<double>(def.members.size());
        row.clusterConsumedJ = clusterConsumed;
        gClusterSnapshots.push_back(row);
    }
}

void
InitializeRunExport()
{
    if (!gEnableRunExport)
    {
        return;
    }

    gCurrentRunExternalId = BuildRunExternalId();
    std::string folderName = gExportRunLabel;
    if (folderName.empty())
    {
        folderName = BuildDefaultRunLabel();
    }

    std::filesystem::path root(gExportRootDir);
    std::filesystem::create_directories(root);
    std::filesystem::path runDir = root / folderName;
    std::filesystem::create_directories(runDir);
    gCurrentRunOutputDir = runDir.string();
}

void
ExportRunFiles()
{
    if (!gEnableRunExport || gCurrentRunOutputDir.empty())
    {
        return;
    }

    const std::filesystem::path runDir(gCurrentRunOutputDir);

    {
        std::ofstream meta(runDir / "run_meta.json");
        meta << "{\n";
        meta << "  \"external_run_id\": \"" << JsonEscape(gCurrentRunExternalId) << "\",\n";
        meta << "  \"schema_version\": \"m1_v1\",\n";
        meta << "  \"scenario_name\": \"cluster-dashboard-m1\",\n";
        meta << "  \"scenario_type\": \"wsn-self-healing\",\n";
        meta << "  \"sim_time_s\": " << std::fixed << std::setprecision(3) << gSimTimeSec << ",\n";
        meta << "  \"node_count\": " << kSensorCount + 1 << ",\n";
        meta << "  \"cluster_count\": " << kClusters << ",\n";
        meta << "  \"traffic_interval_s\": " << gTrafficIntervalSec << ",\n";
        meta << "  \"aggregation_interval_s\": " << gAggregationIntervalSec << ",\n";
        meta << "  \"failure_time_s\": " << gFailureTimeSec << ",\n";
        meta << "  \"recovery_delay_s\": " << gRecoveryDelaySec << ",\n";
        meta << "  \"recovery_enabled\": " << (gEnableRecovery ? "true" : "false") << ",\n";
        meta << "  \"dashboard_interval_s\": " << gDashboardIntervalSec << ",\n";
        meta << "  \"source_file\": \"cluster-dashboard-m1.cc\"\n";
        meta << "}\n";
    }

    {
        std::ofstream nodes(runDir / "nodes_static.csv");
        nodes << "external_run_id,node_id,role,original_cluster_id,original_ch_id,initial_energy_j,x,y,z\n";
        for (const auto& def : gClusterDefs)
        {
            const auto posCh = gSensorNodes.Get(def.chId)->GetObject<MobilityModel>()->GetPosition();
            nodes << gCurrentRunExternalId << "," << def.chId << ",ch," << def.clusterId << "," << def.chId
                  << "," << std::fixed << std::setprecision(6) << gInitialEnergyJ << "," << posCh.x << ","
                  << posCh.y << "," << posCh.z << "\n";

            for (uint32_t memberId : def.members)
            {
                const auto pos = gSensorNodes.Get(memberId)->GetObject<MobilityModel>()->GetPosition();
                nodes << gCurrentRunExternalId << "," << memberId << ",member," << def.clusterId << ","
                      << def.chId << "," << std::fixed << std::setprecision(6) << gInitialEnergyJ << "," << pos.x
                      << "," << pos.y << "," << pos.z << "\n";
            }
        }
        const auto bsPos = gBaseStation->GetObject<MobilityModel>()->GetPosition();
        nodes << gCurrentRunExternalId << "," << kBaseStationId
              << ",bs,,,0.000000," << bsPos.x << "," << bsPos.y << "," << bsPos.z << "\n";
    }

    {
        std::ofstream global(runDir / "global_timeseries.csv");
        global << "external_run_id,sim_time,raw_tx_cum,raw_rx_cum,agg_tx_cum,agg_rx_cum,direct_agg_rx_cum,relayed_agg_rx_cum,relay_fwd_cum,avg_res_j,min_res_j,consumed_j,low_nodes,failed_chs,recovered_clusters,pending_raw_total\n";
        for (const auto& r : gGlobalSnapshots)
        {
            global << gCurrentRunExternalId << "," << std::fixed << std::setprecision(3) << r.simTimeSec << ","
                   << r.rawTxCum << "," << r.rawRxCum << "," << r.aggTxCum << "," << r.aggRxCum << ","
                   << r.directAggRxCum << "," << r.relayedAggRxCum << "," << r.relayFwdCum << ","
                   << std::setprecision(6) << r.avgResJ << "," << r.minResJ << "," << r.consumedJ << ","
                   << r.lowNodes << "," << r.failedChs << "," << r.recoveredClusters << ","
                   << r.pendingRawTotal << "\n";
        }
    }

    {
        std::ofstream cluster(runDir / "cluster_timeseries.csv");
        cluster << "external_run_id,sim_time,cluster_id,original_ch_id,current_ch_id,status,mode,next_hop,members_count,raw_rx_cum,pending_raw,agg_tx_cum,relay_fwd_cum,ch_res_j,avg_mem_res_j,cluster_consumed_j\n";
        for (const auto& r : gClusterSnapshots)
        {
            cluster << gCurrentRunExternalId << "," << std::fixed << std::setprecision(3) << r.simTimeSec << ","
                    << r.clusterId << "," << r.originalChId << "," << r.currentChId << ","
                    << CsvEscape(r.status) << "," << CsvEscape(r.mode) << "," << CsvEscape(r.nextHop) << ","
                    << r.membersCount << "," << r.rawRxCum << "," << r.pendingRaw << "," << r.aggTxCum << ","
                    << r.relayFwdCum << "," << std::setprecision(6) << r.chResJ << "," << r.avgMemResJ << ","
                    << r.clusterConsumedJ << "\n";
        }
    }

    {
        std::ofstream events(runDir / "events.csv");
        events << "external_run_id,sim_time,event_type,severity,cluster_id,node_id,message,details_json\n";
        for (const auto& e : gEventRows)
        {
            events << gCurrentRunExternalId << "," << std::fixed << std::setprecision(3) << e.simTimeSec << ","
                   << CsvEscape(e.eventType) << "," << CsvEscape(e.severity) << ",";
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
        uint64_t pendingRawTotal = 0;
        for (const auto& c : gClusterCounters)
        {
            pendingRawTotal += c.pendingRaw;
        }
        const EnergySnapshot es = GetEnergySnapshot();
        std::ofstream summary(runDir / "run_summary.json");
        summary << "{\n";
        summary << "  \"external_run_id\": \"" << JsonEscape(gCurrentRunExternalId) << "\",\n";
        summary << "  \"final_sim_time\": " << std::fixed << std::setprecision(3) << Simulator::Now().GetSeconds() << ",\n";
        summary << "  \"raw_tx_cum\": " << gGlobalRawTx << ",\n";
        summary << "  \"raw_rx_cum\": " << gGlobalRawRx << ",\n";
        summary << "  \"agg_tx_cum\": " << gGlobalAggTx << ",\n";
        summary << "  \"agg_rx_cum\": " << gGlobalAggRx << ",\n";
        summary << "  \"direct_agg_rx_cum\": " << gGlobalDirectAggRx << ",\n";
        summary << "  \"relayed_agg_rx_cum\": " << gGlobalRelayedAggRx << ",\n";
        summary << "  \"relay_fwd_cum\": " << gGlobalRelayForward << ",\n";
        summary << "  \"failed_chs\": " << gGlobalFailedChCount << ",\n";
        summary << "  \"recovered_clusters\": " << gGlobalRecoveredClusterCount << ",\n";
        summary << "  \"avg_res_j\": " << std::setprecision(6) << es.avgResidualJ << ",\n";
        summary << "  \"min_res_j\": " << es.minResidualJ << ",\n";
        summary << "  \"consumed_j\": " << es.totalConsumedJ << ",\n";
        summary << "  \"low_nodes\": " << es.lowEnergyNodes << ",\n";
        summary << "  \"pending_raw_total\": " << pendingRawTotal << "\n";
        summary << "}\n";
    }

    {
        std::ofstream nodesFinal(runDir / "node_final_summary.csv");
        nodesFinal << "external_run_id,node_id,role,cluster_id,residual_j,consumed_j,final_status\n";
        for (uint32_t i = 0; i < kSensorCount; ++i)
        {
            const uint32_t clusterId = gSensorToCluster[i];
            std::string role = (i == gClusterDefs[clusterId].chId) ? "ch" : "member";
            std::string status = gNodeFailed[i] ? "failed" : "normal";
            if (!gNodeFailed[i] && gResidualEnergyJ[i] <= LowEnergyThresholdJ())
            {
                status = "low_energy";
            }
            nodesFinal << gCurrentRunExternalId << "," << i << "," << role << "," << clusterId << ","
                      << std::fixed << std::setprecision(6) << gResidualEnergyJ[i] << "," << gConsumedEnergyJ[i]
                      << "," << status << "\n";
        }
        nodesFinal << gCurrentRunExternalId << "," << kBaseStationId << ",bs,,0.000000,0.000000,n/a\n";
    }

    std::cout << "[Export] Run artifacts written to: " << gCurrentRunOutputDir << "\n";
}

struct EnergyPercentiles
{
    double p5 = 0.0;
    double p50 = 0.0;
    double p95 = 0.0;
    double minVal = 0.0;
    double maxVal = 0.0;
};

EnergyPercentiles
ComputeEnergyPercentiles()
{
    std::vector<double> energies;
    for (uint32_t i = 0; i < kSensorCount; ++i)
    {
        energies.push_back(gResidualEnergyJ[i]);
    }
    std::sort(energies.begin(), energies.end());

    EnergyPercentiles p;
    if (!energies.empty())
    {
        p.minVal = energies.front();
        p.maxVal = energies.back();
        p.p5 = energies[static_cast<size_t>(energies.size() * 0.05)];
        p.p50 = energies[energies.size() / 2];
        p.p95 = energies[static_cast<size_t>(energies.size() * 0.95)];
    }
    return p;
}

struct TopKNode
{
    uint32_t nodeId;
    std::string role;
    int clusterId;
    double residualJ;
    double consumedJ;
};

std::vector<TopKNode>
GetTopKLowestEnergy(uint32_t k)
{
    std::vector<TopKNode> nodes;
    for (uint32_t i = 0; i < kSensorCount; ++i)
    {
        TopKNode n;
        n.nodeId = i;
        n.residualJ = gResidualEnergyJ[i];
        n.consumedJ = gConsumedEnergyJ[i];
        n.clusterId = (i == kBaseStationId) ? -1 : gSensorToCluster[i];
        if (i == kBaseStationId)
        {
            n.role = "BS";
        }
        else
        {
            const uint32_t clusterId = gSensorToCluster[i];
            n.role = (i == gClusterDefs[clusterId].chId) ? "CH" : "MBR";
        }
        nodes.push_back(n);
    }
    std::sort(nodes.begin(), nodes.end(),
              [](const TopKNode& a, const TopKNode& b) { return a.residualJ < b.residualJ; });
    if (nodes.size() > static_cast<size_t>(k))
    {
        nodes.resize(k);
    }
    return nodes;
}

std::vector<TopKNode>
GetTopKHighestConsumed(uint32_t k)
{
    std::vector<TopKNode> nodes;
    for (uint32_t i = 0; i < kSensorCount; ++i)
    {
        TopKNode n;
        n.nodeId = i;
        n.residualJ = gResidualEnergyJ[i];
        n.consumedJ = gConsumedEnergyJ[i];
        n.clusterId = gSensorToCluster[i];
        const uint32_t clusterId = gSensorToCluster[i];
        n.role = (i == gClusterDefs[clusterId].chId) ? "CH" : "MBR";
        nodes.push_back(n);
    }
    std::sort(nodes.begin(), nodes.end(), [](const TopKNode& a, const TopKNode& b) {
        if (a.consumedJ == b.consumedJ)
        {
            return a.nodeId < b.nodeId;
        }
        return a.consumedJ > b.consumedJ;
    });
    if (nodes.size() > static_cast<size_t>(k))
    {
        nodes.resize(k);
    }
    return nodes;
}

void
ExportNodeEnergyCsv(const std::string& filename)
{
    std::ofstream file(filename);
    if (!file.is_open())
    {
        std::cerr << "Warning: could not open CSV file " << filename << "\n";
        return;
    }

    file << "nodeId,role,clusterId,residualJ,consumedJ,status\n";
    for (uint32_t i = 0; i < kSensorCount; ++i)
    {
        std::string role = "MBR";
        int clusterId = gSensorToCluster[i];
        if (i == kBaseStationId)
        {
            role = "BS";
            clusterId = -1;
        }
        else if (i == gClusterDefs[clusterId].chId)
        {
            role = "CH";
        }

        std::string status = "OK";
        if (gResidualEnergyJ[i] <= LowEnergyThresholdJ())
        {
            status = "LOW_ENERGY";
        }
        if (gNodeFailed[i])
        {
            status = "FAILED";
        }

        file << i << "," << role << "," << clusterId << "," 
             << std::fixed << std::setprecision(6) << gResidualEnergyJ[i] << "," 
             << gConsumedEnergyJ[i] << "," << status << "\n";
    }
    file.close();
    std::cout << "Exported node energy data to " << filename << "\n";
}

void
ExportEventsCsv(const std::string& filename)
{
    std::ofstream file(filename);
    if (!file.is_open())
    {
        std::cerr << "Warning: could not open events CSV file " << filename << "\n";
        return;
    }

    file << "time,event\n";
    for (const auto& evt : gRecentEvents)
    {
        file << evt << "\n";
    }
    file.close();
    std::cout << "Exported " << gRecentEvents.size() << " events to " << filename << "\n";
}

bool
IsWithinHighlightWindow(double tSec)
{
    return tSec + 1e-9 >= gHighlightWindowStartSec && tSec <= gHighlightWindowEndSec + 1e-9;
}

bool
NetAnimReady()
{
    return gEnableNetAnim && gAnim != nullptr;
}

void
SetNodeColorIfAnim(uint32_t nodeId, uint8_t r, uint8_t g, uint8_t b)
{
    if (!NetAnimReady())
    {
        return;
    }
    gAnim->UpdateNodeColor(nodeId, r, g, b);
}

void
SetNodeDescIfAnim(uint32_t nodeId, const std::string& description)
{
    if (!NetAnimReady())
    {
        return;
    }
    gAnim->UpdateNodeDescription(nodeId, description);
}

void
RestoreRelayChVisual()
{
    const uint32_t relayChId = GetRelayChId();
    SetNodeColorIfAnim(relayChId, 255, 0, 0);
    std::ostringstream os;
    os << "CH" << relayChId;
    SetNodeDescIfAnim(relayChId, os.str());
}

void
ApplyRecoveryDisabledVisuals()
{
    // Muted members indicate C2 disconnect when recovery is disabled.
    for (uint32_t memberId : gClusterDefs[kFailureClusterId].members)
    {
        SetNodeColorIfAnim(memberId, 60, 90, 140);
        std::ostringstream os;
        os << "N" << memberId << "(C2 disconnected)";
        SetNodeDescIfAnim(memberId, os.str());
    }
}

void
ApplyRecoveryAppliedVisuals()
{
    for (uint32_t memberId : gClusterDefs[kFailureClusterId].members)
    {
        SetNodeColorIfAnim(memberId, 100, 180, 255);
        std::ostringstream os;
        os << "N" << memberId << "(C2->CH" << GetRelayChId() << ")";
        SetNodeDescIfAnim(memberId, os.str());
    }

    const uint32_t relayChId = GetRelayChId();
    SetNodeColorIfAnim(relayChId, 255, 140, 0);
    SetNodeDescIfAnim(relayChId, "CH6 RECOVERY");
    Simulator::Schedule(Seconds(2.0), &RestoreRelayChVisual);
}

void
ApplyMarkerDescription(double tSec)
{
    if (!NetAnimReady())
    {
        return;
    }

    const double dt = tSec - gFailureTimeSec;
    if (dt < 0.5)
    {
        SetNodeDescIfAnim(kFailureChId, "CH12 FAILED");
        return;
    }

    if (dt < 1.0)
    {
        SetNodeDescIfAnim(kFailureChId, "CH12 FAILED | status=failed");
        return;
    }

    if (!gEnableRecovery)
    {
        SetNodeDescIfAnim(kFailureChId, "CH12 FAILED | C2 disconnected");
        return;
    }

    if (dt < 1.5)
    {
        SetNodeDescIfAnim(GetRelayChId(), "CH6 RECOVERY | C2 recovering");
    }
    else
    {
        SetNodeDescIfAnim(GetRelayChId(), "CH6 RECOVERY | C2 recovered via CH6");
    }
}

void
ScheduleHighlightMarkers()
{
    if (!NetAnimReady())
    {
        return;
    }

    const std::array<double, 4> markerOffsets = {0.0, 0.5, 1.0, 1.5};
    for (double offset : markerOffsets)
    {
        const double at = gFailureTimeSec + offset;
        if (at <= gSimTimeSec)
        {
            Simulator::Schedule(Seconds(at), &ApplyMarkerDescription, at);
        }
    }
}

void
HighlightPacingTick()
{
    const double nowSec = Simulator::Now().GetSeconds();
    if (gRealtime && NetAnimReady() && gHighlightSlowdownFactor > 1.0 && IsWithinHighlightWindow(nowSec))
    {
        const int64_t sleepMs = static_cast<int64_t>(50.0 * (gHighlightSlowdownFactor - 1.0));
        if (sleepMs > 0)
        {
            std::this_thread::sleep_for(std::chrono::milliseconds(sleepMs));
        }
    }

    const double nextTime = nowSec + 0.2;
    if (nextTime <= gHighlightWindowEndSec + 1e-9 && nextTime <= gSimTimeSec + 1e-9)
    {
        Simulator::Schedule(Seconds(0.2), &HighlightPacingTick);
    }
}

void
ScheduleHighlightPacing()
{
    if (!gRealtime || !NetAnimReady())
    {
        return;
    }
    if (gHighlightWindowEndSec <= gHighlightWindowStartSec)
    {
        return;
    }
    const double start = std::max(0.0, gHighlightWindowStartSec);
    if (start <= gSimTimeSec)
    {
        Simulator::Schedule(Seconds(start), &HighlightPacingTick);
    }
}

double
GetNextMemberTrafficIntervalSec(double nowSec)
{
    if (!gHighlightReduceTraffic || gHighlightTrafficMultiplier <= 0.0)
    {
        return gTrafficIntervalSec;
    }
    if (IsWithinHighlightWindow(nowSec))
    {
        return gTrafficIntervalSec * gHighlightTrafficMultiplier;
    }
    return gTrafficIntervalSec;
}

bool
ClusterUsesRelay(uint32_t clusterId)
{
    return clusterId == kRelaySourceCluster && gClusterHealth[clusterId] == ClusterHealth::NORMAL;
}

uint32_t
GetRelayChId()
{
    return gClusterDefs[kRelayViaCluster].chId;
}

std::string
ClusterModeString(uint32_t clusterId)
{
    if (gClusterHealth[clusterId] == ClusterHealth::FAILED)
    {
        return "failed";
    }
    if (gClusterHealth[clusterId] == ClusterHealth::RECOVERING)
    {
        return "recovering";
    }
    return ClusterUsesRelay(clusterId) ? "relay" : "direct";
}

std::string
ClusterNextHopString(uint32_t clusterId)
{
    return FormatNextHop(ClusterNextHopId(clusterId));
}

std::string
ClusterHealthString(uint32_t clusterId)
{
    switch (gClusterHealth[clusterId])
    {
    case ClusterHealth::NORMAL:
        return "normal";
    case ClusterHealth::FAILED:
        return "failed";
    case ClusterHealth::RECOVERING:
        return "recovering";
    case ClusterHealth::RECOVERED:
        return "recovered";
    }
    return "unknown";
}

void
AddEvent(const std::string& msg)
{
    AddTaggedEvent("INFO", msg);
}

void
AddTaggedEvent(const std::string& tag, const std::string& msg)
{
    const double nowSec = Simulator::Now().GetSeconds();
    std::ostringstream os;
    os << "t=" << std::fixed << std::setprecision(1) << nowSec << "s"
       << " [" << tag << "] " << msg;
    gRecentEvents.push_back(os.str());
    while (gRecentEvents.size() > gEventsWindow)
    {
        gRecentEvents.pop_front();
    }

    EventExportRow row;
    row.simTimeSec = nowSec;
    row.eventType = tag;
    if (tag == "FAIL")
    {
        row.severity = "WARN";
    }
    else if (tag == "INFO")
    {
        row.severity = "INFO";
    }
    else
    {
        row.severity = "INFO";
    }
    row.message = msg;
    gEventRows.push_back(row);
}

double
LowEnergyThresholdJ()
{
    return gInitialEnergyJ * gLowEnergyFrac;
}

void
ApplyEnergyConsumption(uint32_t sensorId, double amountJ)
{
    if (sensorId >= kSensorCount || amountJ <= 0.0)
    {
        return;
    }

    const double before = gResidualEnergyJ[sensorId];
    const double delta = std::min(amountJ, before);
    gResidualEnergyJ[sensorId] = std::max(0.0, before - delta);
    gConsumedEnergyJ[sensorId] += delta;

    const double thresholdJ = LowEnergyThresholdJ();
    if (!gLowEnergyAlerted[sensorId] && before > thresholdJ && gResidualEnergyJ[sensorId] <= thresholdJ)
    {
        gLowEnergyAlerted[sensorId] = true;
        const uint32_t clusterId = gSensorToCluster[sensorId];
        std::ostringstream os;
        os << "Energy threshold crossed by node " << sensorId << " (cluster " << clusterId
           << ", residual=" << std::fixed << std::setprecision(3) << gResidualEnergyJ[sensorId] << "J)";
        AddEvent(os.str());
    }

    const uint32_t clusterId = gSensorToCluster[sensorId];
    if (sensorId == gClusterDefs[clusterId].chId)
    {
        const double chWarnThreshold = 0.35 * gInitialEnergyJ;
        if (!gChLowEnergyAlerted[clusterId] && gResidualEnergyJ[sensorId] <= chWarnThreshold)
        {
            gChLowEnergyAlerted[clusterId] = true;
            std::ostringstream os;
            os << "CH low-energy warning: cluster " << clusterId << " CH " << sensorId
               << " residual=" << std::fixed << std::setprecision(3) << gResidualEnergyJ[sensorId] << "J";
            AddEvent(os.str());
        }
    }
}

EnergySnapshot
GetEnergySnapshot()
{
    EnergySnapshot s;
    s.minResidualJ = std::numeric_limits<double>::max();

    for (uint32_t i = 0; i < kSensorCount; ++i)
    {
        s.avgResidualJ += gResidualEnergyJ[i];
        s.totalConsumedJ += gConsumedEnergyJ[i];
        s.minResidualJ = std::min(s.minResidualJ, gResidualEnergyJ[i]);
        if (gResidualEnergyJ[i] <= LowEnergyThresholdJ())
        {
            s.lowEnergyNodes++;
        }
    }

    if (kSensorCount > 0)
    {
        s.avgResidualJ /= static_cast<double>(kSensorCount);
    }
    if (s.minResidualJ == std::numeric_limits<double>::max())
    {
        s.minResidualJ = 0.0;
    }
    return s;
}

void
EnergyTick()
{
    if (gEnableIdleDrain)
    {
        for (uint32_t i = 0; i < kSensorCount; ++i)
        {
            ApplyEnergyConsumption(i, gIdleDrainPerSecondJ * gDashboardIntervalSec);
        }
    }

    const double nextTime = Simulator::Now().GetSeconds() + gDashboardIntervalSec;
    if (nextTime <= gSimTimeSec)
    {
        Simulator::Schedule(Seconds(gDashboardIntervalSec), &EnergyTick);
    }
}

void
RecordRecoveredRawDelivery(uint32_t memberId, uint32_t chId)
{
    const uint32_t clusterId = gSensorToCluster[memberId];
    if (clusterId != kFailureClusterId)
    {
        return;
    }

    gClusterCounters[clusterId].rawRxAtCh++;
    gClusterCounters[clusterId].pendingRaw++;
    gClusterCounters[clusterId].lastRxTimeSec = Simulator::Now().GetSeconds();
    gGlobalRawRx++;
    ApplyEnergyConsumption(chId, gChRawRxEnergyJ);

    if (!gFirstRecoveredRawSeen)
    {
        gFirstRecoveredRawSeen = true;
        AddEvent("First recovered raw packet from cluster 2 arrived at CH6");
    }
}

void
ApplyRecoveryForCluster2()
{
    const uint32_t clusterId = kFailureClusterId;
    if (gClusterHealth[clusterId] != ClusterHealth::RECOVERING)
    {
        return;
    }

    gClusterCurrentCh[clusterId] = GetRelayChId();
    gClusterCounters[clusterId].pendingRaw = 0;
    gClusterHealth[clusterId] = ClusterHealth::RECOVERED;
    gGlobalRecoveredClusterCount = 1;

    std::ostringstream os;
    os << "Recovery applied: cluster " << clusterId << " members reattached to CH " << GetRelayChId();
    AddTaggedEvent("REC", os.str());

    ApplyRecoveryAppliedVisuals();
}

void
TriggerRecoveryForCluster2()
{
    const uint32_t clusterId = kFailureClusterId;
    if (gClusterHealth[clusterId] != ClusterHealth::FAILED)
    {
        return;
    }

    gClusterHealth[clusterId] = ClusterHealth::RECOVERING;
    AddTaggedEvent("REC", "Recovery trigger for cluster 2 started");

    const uint32_t relayChId = GetRelayChId();
    SetNodeColorIfAnim(relayChId, 255, 140, 0);
    SetNodeDescIfAnim(relayChId, "CH6 RECOVERY");
    Simulator::Schedule(MilliSeconds(400), &ApplyRecoveryForCluster2);
}

void
InjectFixedChFailure()
{
    if (gNodeFailed[kFailureChId])
    {
        return;
    }

    gNodeFailed[kFailureChId] = true;
    gClusterHealth[kFailureClusterId] = ClusterHealth::FAILED;
    gClusterCounters[kFailureClusterId].pendingRaw = 0;
    gGlobalFailedChCount = 1;

    SetNodeColorIfAnim(kFailureChId, 128, 128, 128);
    SetNodeDescIfAnim(kFailureChId, "CH12 FAILED | status=failed");
    std::cout << "[NetAnim] CH12 visual state -> FAILED (gray)\n";

    AddTaggedEvent("FAIL", "CH12 failure injected (permanent)");
    AddTaggedEvent("FAIL", "CH12 failure detected by cluster state monitor");

    if (gEnableRecovery)
    {
        Simulator::Schedule(Seconds(gRecoveryDelaySec), &TriggerRecoveryForCluster2);
    }
    else
    {
        ApplyRecoveryDisabledVisuals();
        AddTaggedEvent("INFO", "Recovery disabled: cluster 2 remains failed/disconnected");
    }
}

uint32_t
SensorIndexFromNode(Ptr<Node> node)
{
    for (uint32_t i = 0; i < gSensorNodes.GetN(); ++i)
    {
        if (gSensorNodes.Get(i) == node)
        {
            return i;
        }
    }
    return UINT32_MAX;
}

uint32_t
SensorIndexFromIp(Ipv4Address addr)
{
    for (uint32_t i = 0; i < kSensorCount; ++i)
    {
        if (gIfaces.GetAddress(i) == addr)
        {
            return i;
        }
    }
    return UINT32_MAX;
}

void
RenderDashboard()
{
    std::cout << "\033[2J\033[H";

    const EnergySnapshot es = GetEnergySnapshot();
    const uint64_t rawRxDelta = gGlobalRawRx - gPrevGlobalRawRx;
    const uint64_t aggRxDelta = gGlobalAggRx - gPrevGlobalAggRx;
    gPrevGlobalRawRx = gGlobalRawRx;
    gPrevGlobalAggRx = gGlobalAggRx;

    const double rawDelivery =
        (gGlobalRawTx > 0) ? (100.0 * static_cast<double>(gGlobalRawRx) / static_cast<double>(gGlobalRawTx)) : 0.0;
    const double reductionRatio =
        (gGlobalRawRx > 0) ? (static_cast<double>(gGlobalAggTx) / static_cast<double>(gGlobalRawRx)) : 0.0;

    char globalBuf[768];
    snprintf(globalBuf,
             sizeof(globalBuf),
             "GLOBAL t=%5.1fs raw(TX=%lu RX=%lu del=%.1f%% dRx=%lu) agg(TX=%lu RX=%lu perRaw=%.3f dRx=%lu) paths(dir=%lu rel=%lu fwd=%lu) failCH=%u recCl=%u E(avg=%.3f min=%.3f cons=%.3f) rec=%s",
             Simulator::Now().GetSeconds(),
             gGlobalRawTx,
             gGlobalRawRx,
             rawDelivery,
             rawRxDelta,
             gGlobalAggTx,
             gGlobalAggRx,
             reductionRatio,
             aggRxDelta,
             gGlobalDirectAggRx,
             gGlobalRelayedAggRx,
             gGlobalRelayForward,
             gGlobalFailedChCount,
             gGlobalRecoveredClusterCount,
             es.avgResidualJ,
             es.minResidualJ,
             es.totalConsumedJ,
             gEnableRecovery ? "ON" : "OFF");
    std::cout << globalBuf << "\n";

    std::vector<std::string> clusterLines;
    char buf[256];

    snprintf(buf,
             sizeof(buf),
             "%-3s %-10s %-6s %-8s %-10s %-10s %-8s %-8s %-7s %-7s %-7s %-8s %-7s %-7s %-8s",
             "CID",
             "Status",
             "OrigCH",
             "ActiveCH",
             "Mode",
             "NextHop",
             "CHResJ",
             "AvgMemJ",
             "RawRx",
             "Pending",
             "AggTx",
             "RelayFwd",
             "LastRx",
             "LastAgg",
             "LastBsRx");
    clusterLines.push_back(buf);

    for (const auto& def : gClusterDefs)
    {
        const auto& c = gClusterCounters[def.clusterId];
        const uint32_t chId = def.chId;
        const uint32_t activeCh = gClusterCurrentCh[def.clusterId];
        double memberResidualSum = 0.0;
        for (uint32_t memberId : def.members)
        {
            memberResidualSum += gResidualEnergyJ[memberId];
        }
        const double avgMemberResidual =
            def.members.empty() ? 0.0 : (memberResidualSum / static_cast<double>(def.members.size()));

        double clusterConsumed = gConsumedEnergyJ[chId];
        for (uint32_t memberId : def.members)
        {
            clusterConsumed += gConsumedEnergyJ[memberId];
        }

        const std::string statusStr = FormatClusterStatus(def.clusterId);
        const std::string modeStr = FormatModeString(def.clusterId);
        const std::string nextHopStr = FormatNextHop(ClusterNextHopId(def.clusterId));
        const std::string lastRxStr = FormatLastTime(c.lastRxTimeSec);
        const std::string lastAggStr = FormatLastTime(c.lastAggTimeSec);
        const std::string lastBsStr = FormatLastTime(c.lastAggDeliveredTimeSec);

        snprintf(buf,
                 sizeof(buf),
                 "%-3u %-10s %-6u %-8u %-10s %-10s %-8.3f %-8.3f %-7lu %-7lu %-7lu %-8lu %-7s %-7s %-8s",
                 def.clusterId,
                 statusStr.c_str(),
                 def.chId,
                 activeCh,
                 modeStr.c_str(),
                 nextHopStr.c_str(),
                 gResidualEnergyJ[activeCh],
                 avgMemberResidual,
                 c.rawRxAtCh,
                 c.pendingRaw,
                 c.aggTxToBs,
                 c.relayForwardCount,
                 lastRxStr.c_str(),
                 lastAggStr.c_str(),
                 lastBsStr.c_str());
        clusterLines.push_back(buf);
    }

    PrintBox("CLUSTER STATUS", clusterLines);

    std::vector<std::string> eventLines;
    if (gRecentEvents.empty())
    {
        eventLines.push_back("(no events)");
    }
    else
    {
        for (const auto& e : gRecentEvents)
        {
            eventLines.push_back(e);
        }
    }
    PrintBox("RECENT EVENTS (WINDOW)", eventLines);

    std::cout.flush();
}

void
DashboardTick()
{
    UpdateDisconnectedAccounting(Simulator::Now().GetSeconds());
    CaptureSnapshot(Simulator::Now().GetSeconds());
    RenderDashboard();
    if (Simulator::Now().GetSeconds() + 1e-9 < gSimTimeSec)
    {
        Simulator::Schedule(Seconds(gDashboardIntervalSec), &DashboardTick);
    }
}

void
OnChReceive(Ptr<Socket> socket)
{
    Address from;
    while (Ptr<Packet> packet = socket->RecvFrom(from))
    {
        (void)packet;
        const uint32_t chId = SensorIndexFromNode(socket->GetNode());
        if (chId == UINT32_MAX)
        {
            continue;
        }
        if (gNodeFailed[chId])
        {
            continue;
        }
        const uint32_t chClusterId = gSensorToCluster[chId];
        uint32_t accountingClusterId = chClusterId;

        const auto srcAddr = InetSocketAddress::ConvertFrom(from).GetIpv4();
        const uint32_t srcId = SensorIndexFromIp(srcAddr);
        if (srcId != UINT32_MAX)
        {
            const uint32_t srcCluster = gSensorToCluster[srcId];
            if (srcCluster < kClusters)
            {
                accountingClusterId = srcCluster;
            }
        }

        gClusterCounters[accountingClusterId].rawRxAtCh++;
        gClusterCounters[accountingClusterId].pendingRaw++;
        gClusterCounters[accountingClusterId].lastRxTimeSec = Simulator::Now().GetSeconds();
        gGlobalRawRx++;
        ApplyEnergyConsumption(chId, gChRawRxEnergyJ);

        if (srcId != UINT32_MAX)
        {
            const uint32_t originCluster = gSensorToCluster[srcId];
            if (originCluster == kFailureClusterId && gClusterHealth[originCluster] == ClusterHealth::RECOVERED &&
                chId == GetRelayChId() && !gFirstRecoveredRawSeen)
            {
                gFirstRecoveredRawSeen = true;
                AddTaggedEvent("RAW", "First recovered raw packet from cluster 2 arrived at CH6");
            }
        }
        if (srcId != UINT32_MAX && (gClusterCounters[accountingClusterId].rawRxAtCh % 15 == 0))
        {
            std::ostringstream os;
            os << "Cluster " << accountingClusterId << " CH " << chId << " reached "
               << gClusterCounters[accountingClusterId].rawRxAtCh
               << " raw receptions (latest from node " << srcId << ")";
                AddTaggedEvent("RAW", os.str());
        }
    }
}

void
OnBsReceive(Ptr<Socket> socket)
{
    Address from;
    while (Ptr<Packet> packet = socket->RecvFrom(from))
    {
        AggregateMetaHeader meta;
        if (packet->GetSize() >= meta.GetSerializedSize())
        {
            packet->RemoveHeader(meta);
        }

        const auto srcAddr = InetSocketAddress::ConvertFrom(from).GetIpv4();
        const uint32_t chId = SensorIndexFromIp(srcAddr);
        if (chId == UINT32_MAX)
        {
            continue;
        }

        uint32_t clusterId = gSensorToCluster[chId];
        if (meta.GetOriginClusterId() < kClusters)
        {
            clusterId = meta.GetOriginClusterId();
        }

        gGlobalAggRx++;
        gClusterCounters[clusterId].lastAggDeliveredTimeSec = Simulator::Now().GetSeconds();

        if (meta.GetRelayed())
        {
            gGlobalRelayedAggRx++;
            if (!gClusterCounters[clusterId].firstRelayDelivered)
            {
                gClusterCounters[clusterId].firstRelayDelivered = true;
                std::ostringstream os;
                os << "First relay-delivered aggregate reached BS for cluster " << clusterId;
                AddTaggedEvent("RELAY", os.str());
            }
        }
        else
        {
            gGlobalDirectAggRx++;
        }

        if (!gClusterCounters[clusterId].firstAggDelivered)
        {
            gClusterCounters[clusterId].firstAggDelivered = true;
            std::ostringstream os;
            os << "First aggregate delivered to BS from cluster " << clusterId << " (CH " << chId << ")";
            AddTaggedEvent("AGG", os.str());
        }
        else if (gClusterCounters[clusterId].aggTxToBs % 5 == 0)
        {
            std::ostringstream os;
            os << "BS received aggregate milestone from cluster " << clusterId
               << " totalAggTx=" << gClusterCounters[clusterId].aggTxToBs;
            AddTaggedEvent("AGG", os.str());
        }
    }
}

void
RelayReceiveAndForward(uint32_t originClusterId, Ptr<Packet> packet)
{
    const uint32_t relayChId = GetRelayChId();
    const uint32_t relayClusterId = kRelayViaCluster;

    if (originClusterId >= kClusters || packet == nullptr)
    {
        return;
    }

    gClusterCounters[relayClusterId].relayRxCount++;
    ApplyEnergyConsumption(relayChId, gRelayAggRxEnergyJ);

    if (!gClusterCounters[originClusterId].firstRelayAggReceived)
    {
        gClusterCounters[originClusterId].firstRelayAggReceived = true;
        std::ostringstream os;
        os << "First aggregate from cluster " << originClusterId << " received at relay CH " << relayChId;
        AddTaggedEvent("RELAY", os.str());
    }

    AggregateMetaHeader meta;
    if (packet->GetSize() >= meta.GetSerializedSize())
    {
        packet->RemoveHeader(meta);
    }
    meta.SetRelayed(true);
    packet->AddHeader(meta);

    auto it = gChToBsSockets.find(relayChId);
    if (it == gChToBsSockets.end())
    {
        return;
    }

    const int sent = it->second->Send(packet);
    if (sent > 0)
    {
        ApplyEnergyConsumption(relayChId, gRelayForwardTxEnergyJ);
        gGlobalRelayForward++;
        gClusterCounters[relayClusterId].relayForwardCount++;

        if (!gClusterCounters[originClusterId].firstRelayForwarded)
        {
            gClusterCounters[originClusterId].firstRelayForwarded = true;
            std::ostringstream os;
            os << "First aggregate from cluster " << originClusterId << " forwarded by relay CH " << relayChId;
            AddTaggedEvent("RELAY", os.str());
        }
        else if (gClusterCounters[relayClusterId].relayForwardCount % 5 == 0)
        {
            std::ostringstream os;
            os << "Relay CH " << relayChId << " forwarding milestone count="
               << gClusterCounters[relayClusterId].relayForwardCount;
            AddTaggedEvent("RELAY", os.str());
        }
    }
}

void
AggregateAndSendFromCh(uint32_t clusterId)
{
    auto& counters = gClusterCounters[clusterId];
    const uint32_t chId = gClusterCurrentCh[clusterId];

    if (gNodeFailed[chId])
    {
        const double nextTime = Simulator::Now().GetSeconds() + gAggregationIntervalSec;
        if (nextTime <= gSimTimeSec)
        {
            Simulator::Schedule(Seconds(gAggregationIntervalSec), &AggregateAndSendFromCh, clusterId);
        }
        return;
    }

    if (counters.pendingRaw > 0)
    {
        const uint64_t pendingBefore = counters.pendingRaw;
        const double aggCost = static_cast<double>(pendingBefore) * gChAggregationEnergyPerRawJ;
        ApplyEnergyConsumption(chId, aggCost);

        Ptr<Packet> packet = Create<Packet>(gAggregatePayloadBytes);
        AggregateMetaHeader meta;
        meta.SetOriginClusterId(static_cast<uint8_t>(clusterId));
        meta.SetOriginChId(static_cast<uint8_t>(chId));
        meta.SetRelayed(false);
        packet->AddHeader(meta);

        bool useRelay = ClusterUsesRelay(clusterId);
        auto it = gChToBsSockets.find(chId);
        if (it != gChToBsSockets.end())
        {
            int sent = -1;
            if (!useRelay)
            {
                sent = it->second->Send(packet);
            }
            else
            {
                // Deterministic logical relay hop: source CH transmits to fixed relay CH,
                // then relay CH forwards to BS through the existing BS socket callback path.
                sent = 1;
                Simulator::Schedule(MilliSeconds(20), &RelayReceiveAndForward, clusterId, packet->Copy());
            }
            if (sent > 0)
            {
                ApplyEnergyConsumption(chId, gChAggTxEnergyJ);
                counters.aggTxToBs++;
                counters.lastAggTimeSec = Simulator::Now().GetSeconds();
                gGlobalAggTx++;
                counters.pendingRaw = 0; // deterministic flush for this milestone

                if (!counters.firstAggCreated)
                {
                    counters.firstAggCreated = true;
                    std::ostringstream os;
                    os << "First aggregate created by cluster " << clusterId << " (CH " << chId
                       << ", mode=" << ClusterModeString(clusterId)
                       << ", consumedRaw=" << pendingBefore << ")";
                    AddTaggedEvent("AGG", os.str());
                }
                else
                {
                    std::ostringstream os;
                    os << "Aggregate sent cluster " << clusterId << " by CH " << chId
                       << " via " << ClusterNextHopString(clusterId)
                       << " consumedRaw=" << pendingBefore;
                    AddTaggedEvent("AGG", os.str());
                }

                if (useRelay && !counters.firstRelayAggCreated)
                {
                    counters.firstRelayAggCreated = true;
                    std::ostringstream os;
                    os << "First relay-path aggregate created by cluster " << clusterId
                       << " (source CH " << chId << " -> relay CH " << GetRelayChId() << ")";
                          AddTaggedEvent("RELAY", os.str());
                }

                if (clusterId == kFailureClusterId && gClusterHealth[clusterId] == ClusterHealth::RECOVERED &&
                    !gFirstRecoveredAggSent)
                {
                    gFirstRecoveredAggSent = true;
                    AddTaggedEvent("REC", "First recovered aggregate path active: cluster 2 via CH6 direct to BS");
                }
            }
        }
    }

    const double nextTime = Simulator::Now().GetSeconds() + gAggregationIntervalSec;
    if (nextTime <= gSimTimeSec)
    {
        Simulator::Schedule(Seconds(gAggregationIntervalSec), &AggregateAndSendFromCh, clusterId);
    }
}

void
SendMemberToCh(uint32_t memberId)
{
    const uint32_t clusterId = gSensorToCluster[memberId];
    const uint32_t chId = gClusterCurrentCh[clusterId];

    if (gNodeFailed[memberId] || gNodeFailed[chId] || gClusterHealth[clusterId] == ClusterHealth::FAILED)
    {
        if (gClusterHealth[clusterId] == ClusterHealth::FAILED || gClusterHealth[clusterId] == ClusterHealth::RECOVERING ||
            gNodeFailed[chId])
        {
            gRawDroppedCum++;
            gClusterRawDroppedCum[clusterId]++;
        }
        const double nowSec = Simulator::Now().GetSeconds();
        const double nextTimeSkip = nowSec + GetNextMemberTrafficIntervalSec(nowSec);
        if (nextTimeSkip <= gTrafficStopTimeSec)
        {
            Simulator::Schedule(Seconds(GetNextMemberTrafficIntervalSec(nowSec)), &SendMemberToCh, memberId);
        }
        return;
    }

    auto it = gMemberSockets.find(memberId);
    if (it == gMemberSockets.end())
    {
        return;
    }

    Ptr<Packet> packet = Create<Packet>(gPayloadBytes);
    int sent = -1;
    const bool deterministicRecoveredPath =
        (clusterId == kFailureClusterId && gClusterHealth[clusterId] == ClusterHealth::RECOVERED &&
         chId == GetRelayChId());

    if (deterministicRecoveredPath)
    {
        sent = 1;
        Simulator::Schedule(MilliSeconds(12), &RecordRecoveredRawDelivery, memberId, chId);
    }
    else
    {
        sent = it->second->SendTo(packet, 0, InetSocketAddress(gIfaces.GetAddress(chId), kChPort));
    }
    if (sent > 0)
    {
        ApplyEnergyConsumption(memberId, gMemberRawTxEnergyJ);
        gGlobalRawTx++;
        gClusterCounters[clusterId].rawTxToCh++;
        if (!gFirstTxSeen[memberId])
        {
            gFirstTxSeen[memberId] = true;
            std::ostringstream os;
            os << "Node " << memberId << " (member) started periodic traffic to CH " << chId;
            AddEvent(os.str());
        }
    }

    const double nowSec = Simulator::Now().GetSeconds();
    const double nextIntervalSec = GetNextMemberTrafficIntervalSec(nowSec);
    const double nextTime = nowSec + nextIntervalSec;
    if (nextTime <= gTrafficStopTimeSec)
    {
        Simulator::Schedule(Seconds(nextIntervalSec), &SendMemberToCh, memberId);
    }
}

void
PrintStartupSummary()
{
    std::vector<std::string> lines;
    std::ostringstream os;
    os << "Sensors=" << kSensorCount << " clusters=" << kClusters << " nodes/cluster=" << kNodesPerCluster;
    lines.push_back(os.str());
    lines.push_back("Base Station: " + FormatNextHop(kBaseStationId));

    os.str("");
    os.clear();
    os << "Intervals: traffic=" << std::fixed << std::setprecision(1) << gTrafficIntervalSec << "s"
       << " aggregation=" << gAggregationIntervalSec << "s"
       << " dashboard=" << gDashboardIntervalSec << "s";
    lines.push_back(os.str());

    os.str("");
    os.clear();
    os << "Failure/Recovery: failureTime=" << std::fixed << std::setprecision(1) << gFailureTimeSec
       << "s recoveryDelay=" << gRecoveryDelaySec << "s enableRecovery=" << (gEnableRecovery ? "true" : "false");
    lines.push_back(os.str());

    os.str("");
    os.clear();
    os << "Low-energy threshold: frac=" << std::fixed << std::setprecision(2) << gLowEnergyFrac
       << " => " << std::setprecision(3) << LowEnergyThresholdJ() << "J (initial=" << gInitialEnergyJ << "J)";
    lines.push_back(os.str());

    lines.push_back(std::string("NetAnim: ") + (gEnableNetAnim ? ("enabled xml=" + gNetAnimFile) : "disabled"));
    lines.push_back("Relay baseline: Cluster2 OrigCH12 routes via CH6 to BS while status=normal");

    if (gColorEnabled)
    {
        lines.push_back("Legend: " + Colorize("FAILED", GetColorCode("FAILED")) + ", " +
                        Colorize("RECOVERED", GetColorCode("RECOVERED")) + ", " +
                        Colorize("RECOVERING", GetColorCode("RECOVERING")) + ", " +
                        Colorize("NORMAL", GetColorCode("NORMAL")));
    }

    PrintBox("STARTUP TOPOLOGY SUMMARY", lines);

    std::vector<std::string> topoLines;
    for (const auto& def : gClusterDefs)
    {
        std::ostringstream row;
        if (kSensorCount <= 100)
        {
            const uint32_t first = def.members.empty() ? def.chId : def.members.front();
            const uint32_t last = def.members.empty() ? def.chId : def.members.back();
            row << "Cluster" << def.clusterId << ": members=" << def.members.size() << " range=" << first << ".."
                << last;
        }
        else
        {
            row << "Cluster" << def.clusterId << ": members=" << def.members.size();
        }
        topoLines.push_back(row.str());
    }
    topoLines.push_back("--- Topology Map ---");
    topoLines.push_back("Cluster0: CH0 -> BS");
    topoLines.push_back("Cluster1: CH6 -> BS");
    topoLines.push_back("Cluster2: CH12 -> CH6 -> BS (relay baseline)");
    PrintBox("CLUSTER-LEVEL TOPOLOGY MAP", topoLines);
}

void
ConfigureNetAnim(AnimationInterface& anim)
{
    anim.SetMobilityPollInterval(Seconds(gNetAnimPollIntervalSec));
    anim.EnablePacketMetadata(gNetAnimPacketMetadata);
    anim.SetMaxPktsPerTraceFile(gNetAnimMaxPktsPerTraceFile);

    // Stable role labels/colors make topology state easier to inspect in NetAnim.
    SetNodeDescIfAnim(kBaseStationId, "BASE_STATION");
    SetNodeColorIfAnim(kBaseStationId, 0, 200, 0);

    for (const auto& def : gClusterDefs)
    {
        std::ostringstream chLabel;
        chLabel << "CH" << def.chId;
        SetNodeDescIfAnim(def.chId, chLabel.str());
        SetNodeColorIfAnim(def.chId, 255, 0, 0);

        for (uint32_t memberId : def.members)
        {
            std::ostringstream mLabel;
            mLabel << "N" << memberId << "(C" << def.clusterId << ")";
            SetNodeDescIfAnim(memberId, mLabel.str());
            SetNodeColorIfAnim(memberId, 0, 120, 255);
        }
    }
}

void
BuildClusterDefinitions()
{
    gClusterDefs[0] = {0, 0, {1, 2, 3, 4, 5}};
    gClusterDefs[1] = {1, 6, {7, 8, 9, 10, 11}};
    gClusterDefs[2] = {2, 12, {13, 14, 15, 16, 17}};

    for (const auto& def : gClusterDefs)
    {
        gSensorToCluster[def.chId] = def.clusterId;
        gClusterCurrentCh[def.clusterId] = def.chId;
        gClusterHealth[def.clusterId] = ClusterHealth::NORMAL;
        for (uint32_t m : def.members)
        {
            gSensorToCluster[m] = def.clusterId;
        }
    }
}

void
InstallDeterministicMobility()
{
    MobilityHelper sensorMobility;
    Ptr<ListPositionAllocator> sensorAlloc = CreateObject<ListPositionAllocator>();

    const std::vector<Vector> positions = {
        Vector(18.0, 18.0, 0.0), // cluster 0 CH
        Vector(14.0, 21.0, 0.0),
        Vector(21.0, 23.0, 0.0),
        Vector(17.0, 25.0, 0.0),
        Vector(24.0, 18.0, 0.0),
        Vector(20.0, 15.0, 0.0),

        Vector(80.0, 20.0, 0.0), // cluster 1 CH
        Vector(75.0, 18.0, 0.0),
        Vector(84.0, 24.0, 0.0),
        Vector(78.0, 26.0, 0.0),
        Vector(86.0, 18.0, 0.0),
        Vector(82.0, 15.0, 0.0),

        Vector(50.0, 72.0, 0.0), // cluster 2 CH
        Vector(45.0, 69.0, 0.0),
        Vector(54.0, 68.0, 0.0),
        Vector(48.0, 76.0, 0.0),
        Vector(56.0, 74.0, 0.0),
        Vector(51.0, 66.0, 0.0),
    };

    for (const auto& p : positions)
    {
        sensorAlloc->Add(p);
    }

    sensorMobility.SetPositionAllocator(sensorAlloc);
    sensorMobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
    sensorMobility.Install(gSensorNodes);

    MobilityHelper bsMobility;
    Ptr<ListPositionAllocator> bsAlloc = CreateObject<ListPositionAllocator>();
    bsAlloc->Add(Vector(50.0, 50.0, 0.0));
    bsMobility.SetPositionAllocator(bsAlloc);
    bsMobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
    bsMobility.Install(gBaseStation);
}

void
InstallSockets()
{
    TypeId udpFactory = TypeId::LookupByName("ns3::UdpSocketFactory");

    gBsRxSocket = Socket::CreateSocket(gBaseStation, udpFactory);
    gBsRxSocket->Bind(InetSocketAddress(Ipv4Address::GetAny(), kBsPort));
    gBsRxSocket->SetRecvCallback(MakeCallback(&OnBsReceive));
    const Ipv4Address bsAddr = gIfaces.GetAddress(kBaseStationId);

    for (const auto& def : gClusterDefs)
    {
        Ptr<Node> chNode = gSensorNodes.Get(def.chId);
        Ptr<Socket> chRx = Socket::CreateSocket(chNode, udpFactory);
        chRx->Bind(InetSocketAddress(Ipv4Address::GetAny(), kChPort));
        chRx->SetRecvCallback(MakeCallback(&OnChReceive));
        gChSockets[def.chId] = chRx;

        Ptr<Socket> chToBsTx = Socket::CreateSocket(chNode, udpFactory);
        chToBsTx->Connect(InetSocketAddress(bsAddr, kBsPort));
        gChToBsSockets[def.chId] = chToBsTx;

        Ipv4Address chAddr = gIfaces.GetAddress(def.chId);
        for (uint32_t memberId : def.members)
        {
            Ptr<Node> memberNode = gSensorNodes.Get(memberId);
            Ptr<Socket> tx = Socket::CreateSocket(memberNode, udpFactory);
            tx->Connect(InetSocketAddress(chAddr, kChPort));
            gMemberSockets[memberId] = tx;
        }
    }
}

void
SchedulePeriodicMemberTraffic()
{
    for (const auto& def : gClusterDefs)
    {
        uint32_t slot = 0;
        for (uint32_t memberId : def.members)
        {
            const double firstSend = 1.0 + (0.2 * static_cast<double>(def.clusterId)) + (0.15 * slot);
            Simulator::Schedule(Seconds(firstSend), &SendMemberToCh, memberId);
            ++slot;
        }
    }
}

void
SchedulePeriodicAggregationTraffic()
{
    for (const auto& def : gClusterDefs)
    {
        const double firstAggTime = 4.0 + (0.2 * static_cast<double>(def.clusterId));
        Simulator::Schedule(Seconds(firstAggTime), &AggregateAndSendFromCh, def.clusterId);
    }
}

} // namespace

int
main(int argc, char* argv[])
{
    // Validation commands:
    // ./ns3 run "scratch/cluster-dashboard-m1 --simTime=30 --trafficInterval=3 --aggregationInterval=6 --dashboardInterval=1 --failureTime=13 --recoveryDelay=1 --enableRecovery=true --realtime=true"
    // ./ns3 run "scratch/cluster-dashboard-m1 --simTime=30 --trafficInterval=3 --aggregationInterval=6 --dashboardInterval=1 --failureTime=13 --recoveryDelay=1 --enableRecovery=false --realtime=true"
    CommandLine cmd(__FILE__);
    cmd.AddValue("simTime", "Simulation duration in seconds", gSimTimeSec);
    cmd.AddValue("trafficInterval", "Member-to-CH send interval in seconds", gTrafficIntervalSec);
    cmd.AddValue("dashboardInterval", "Dashboard refresh period in seconds", gDashboardIntervalSec);
    cmd.AddValue("aggregationInterval", "CH aggregation/send interval in seconds", gAggregationIntervalSec);
    cmd.AddValue("payloadBytes", "UDP payload bytes for member reports", gPayloadBytes);
    cmd.AddValue("aggregatePayloadBytes", "UDP payload bytes for aggregate CH->BS packet", gAggregatePayloadBytes);
    cmd.AddValue("initialEnergyJ", "Initial energy per sensor (J)", gInitialEnergyJ);
    cmd.AddValue("memberRawTxEnergyJ", "Energy spent by member per raw TX (J)", gMemberRawTxEnergyJ);
    cmd.AddValue("chRawRxEnergyJ", "Energy spent by CH per raw RX (J)", gChRawRxEnergyJ);
    cmd.AddValue("chAggregationEnergyPerRawJ", "CH aggregation energy per pending raw packet (J)", gChAggregationEnergyPerRawJ);
    cmd.AddValue("chAggTxEnergyJ", "Energy spent by CH per aggregate TX to BS (J)", gChAggTxEnergyJ);
    cmd.AddValue("relayAggRxEnergyJ", "Relay CH energy per relayed aggregate RX (J)", gRelayAggRxEnergyJ);
    cmd.AddValue("relayForwardTxEnergyJ", "Relay CH energy per forwarded aggregate TX (J)", gRelayForwardTxEnergyJ);
    cmd.AddValue("enableIdleDrain", "Enable fixed idle drain accounting (true/false)", gEnableIdleDrain);
    cmd.AddValue("idleDrainPerSecondJ", "Idle energy drain per sensor per second (J)", gIdleDrainPerSecondJ);
    cmd.AddValue("lowEnergyThresholdPct", "Low-energy threshold percentage of initial energy", gLowEnergyThresholdPct);
    cmd.AddValue("trafficStopLeadSec", "How many seconds before end member TX stops (drain window)", gTrafficStopLeadSec);
    cmd.AddValue("failureTime", "Fixed CH12 failure time in seconds", gFailureTimeSec);
    cmd.AddValue("recoveryDelay", "Delay from failure to recovery trigger in seconds", gRecoveryDelaySec);
    cmd.AddValue("enableRecovery", "Enable deterministic local recovery (true/false)", gEnableRecovery);
    cmd.AddValue("maxRange", "Wireless communication range in meters", gMaxRangeMeters);
    cmd.AddValue("realtime", "Use RealtimeSimulatorImpl (true/false)", gRealtime);
    cmd.AddValue("enableNetAnim", "Enable NetAnim XML trace output (true/false)", gEnableNetAnim);
    cmd.AddValue("netAnimFile", "NetAnim XML trace file path", gNetAnimFile);
    cmd.AddValue("netAnimPacketMetadata", "Include packet metadata in NetAnim trace (true/false)", gNetAnimPacketMetadata);
    cmd.AddValue("netAnimMaxPktsPerTraceFile", "Max packets per NetAnim trace file", gNetAnimMaxPktsPerTraceFile);
    cmd.AddValue("netAnimPollInterval", "NetAnim mobility polling interval in seconds", gNetAnimPollIntervalSec);
    cmd.AddValue("highlightWindowStart", "Highlight window start time in seconds", gHighlightWindowStartSec);
    cmd.AddValue("highlightWindowEnd", "Highlight window end time in seconds", gHighlightWindowEndSec);
    cmd.AddValue("highlightSlowdownFactor", "Wall-clock slowdown factor inside highlight window (realtime only)", gHighlightSlowdownFactor);
    cmd.AddValue("highlightReduceTraffic", "Reduce member traffic density inside highlight window (true/false)", gHighlightReduceTraffic);
    cmd.AddValue("highlightTrafficMultiplier", "Traffic interval multiplier when highlightReduceTraffic is enabled", gHighlightTrafficMultiplier);
    cmd.AddValue("color", "Enable ANSI color in terminal output (true/false)", gColorEnabled);
    cmd.AddValue("noColor", "Disable ANSI color in terminal output (true/false)", gNoColor);
    cmd.AddValue("dashboardStyle", "Dashboard style: 'combined' (new boxed) or 'classic' (old unstructured)", gDashboardStyle);
    cmd.AddValue("eventsWindow", "Recent event window size", gEventsWindow);
    cmd.AddValue("topK", "Number of top-K lowest energy nodes to show in end report", gTopK);
    cmd.AddValue("lowEnergyFrac", "Low-energy threshold as fraction of initial energy", gLowEnergyFrac);
    cmd.AddValue("energyCsv", "Optional per-node energy CSV filename", gEnergyCsv);
    cmd.AddValue("exportNodeEnergyCsv", "Export per-node energy data to CSV file (path, empty=disabled)", gExportNodeEnergyCsv);
    cmd.AddValue("exportEventsCsv", "Export recent events to CSV file (path, empty=disabled)", gExportEventsCsv);
    cmd.AddValue("enableRunExport", "Enable Milestone 2 structured run export (true/false)", gEnableRunExport);
    cmd.AddValue("exportRootDir", "Root directory for run export folders", gExportRootDir);
    cmd.AddValue("exportRunLabel", "Optional explicit output folder name for this run", gExportRunLabel);
    cmd.Parse(argc, argv);

    // Backward compatibility for previous threshold flag.
    gLowEnergyFrac = std::max(0.0, std::min(1.0, gLowEnergyFrac));
    if (std::abs(gLowEnergyThresholdPct - 25.0) > 1e-9)
    {
        gLowEnergyFrac = std::max(0.0, std::min(1.0, gLowEnergyThresholdPct / 100.0));
    }

    if (!gEnergyCsv.empty())
    {
        gExportNodeEnergyCsv = gEnergyCsv;
    }

    if (gNoColor)
    {
        gColorEnabled = false;
    }
    if (gColorEnabled && !IsTerminal())
    {
        gColorEnabled = false;
    }

    InitializeRunExport();

    gTrafficStopTimeSec = std::max(0.0, gSimTimeSec - gTrafficStopLeadSec);

    if (gRealtime)
    {
        GlobalValue::Bind("SimulatorImplementationType", StringValue("ns3::RealtimeSimulatorImpl"));
    }

    BuildClusterDefinitions();

    for (uint32_t i = 0; i < kSensorCount; ++i)
    {
        gResidualEnergyJ[i] = gInitialEnergyJ;
        gConsumedEnergyJ[i] = 0.0;
    }

    gSensorNodes.Create(kSensorCount);
    gBaseStation = CreateObject<Node>();

    NodeContainer allNodes;
    allNodes.Add(gSensorNodes);
    allNodes.Add(gBaseStation);

    InstallDeterministicMobility();

    WifiHelper wifi;
    wifi.SetStandard(WIFI_STANDARD_80211b);
    wifi.SetRemoteStationManager("ns3::ConstantRateWifiManager",
                                 "DataMode",
                                 StringValue("DsssRate1Mbps"),
                                 "ControlMode",
                                 StringValue("DsssRate1Mbps"));

    YansWifiChannelHelper channel = YansWifiChannelHelper::Default();
    channel.AddPropagationLoss("ns3::RangePropagationLossModel", "MaxRange", DoubleValue(gMaxRangeMeters));

    YansWifiPhyHelper phy;
    phy.SetChannel(channel.Create());

    WifiMacHelper mac;
    mac.SetType("ns3::AdhocWifiMac");

    NetDeviceContainer sensorDevices = wifi.Install(phy, mac, gSensorNodes);
    NetDeviceContainer bsDevice = wifi.Install(phy, mac, gBaseStation);

    NetDeviceContainer allDevices;
    allDevices.Add(sensorDevices);
    allDevices.Add(bsDevice);

    InternetStackHelper stack;
    stack.Install(allNodes);

    Ipv4AddressHelper ipv4;
    ipv4.SetBase("10.1.0.0", "255.255.255.0");
    gIfaces = ipv4.Assign(allDevices);

    InstallSockets();

    std::unique_ptr<AnimationInterface> anim;
    if (gEnableNetAnim)
    {
        if (gNetAnimFile.empty())
        {
            gNetAnimFile = "cluster-dashboard-m1.xml";
        }
        anim = std::make_unique<AnimationInterface>(gNetAnimFile);
        gAnim = anim.get();
        ConfigureNetAnim(*anim);
        ScheduleHighlightMarkers();
        ScheduleHighlightPacing();
    }

    SchedulePeriodicMemberTraffic();
    SchedulePeriodicAggregationTraffic();
    EnergyTick();
    Simulator::Schedule(Seconds(gFailureTimeSec), &InjectFixedChFailure);

    AddEvent("Simulation initialized with fixed 3-cluster topology");
    CaptureSnapshot(0.0);
    PrintStartupSummary();
    DashboardTick();

    Simulator::Stop(Seconds(gSimTimeSec));
    Simulator::Run();

    UpdateDisconnectedAccounting(Simulator::Now().GetSeconds());
    CaptureSnapshot(Simulator::Now().GetSeconds());
    RenderDashboard();

    {
        std::vector<std::string> lines;
        char buf[256];
        const double rawDelivery =
            (gGlobalRawTx > 0) ? (100.0 * static_cast<double>(gGlobalRawRx) / static_cast<double>(gGlobalRawTx)) : 0.0;
        const double reductionRatio =
            (gGlobalRawRx > 0) ? (static_cast<double>(gGlobalAggTx) / static_cast<double>(gGlobalRawRx)) : 0.0;

        snprintf(buf, sizeof(buf), "SimEnd=%.1fs Raw(TX=%lu RX=%lu Delivery=%.1f%%)", Simulator::Now().GetSeconds(), gGlobalRawTx, gGlobalRawRx, rawDelivery);
        lines.push_back(buf);
        snprintf(buf, sizeof(buf), "Agg(TX=%lu RX=%lu AggPerRawRx=%.3f) Paths(direct=%lu relayed=%lu relayFwd=%lu)",
                 gGlobalAggTx,
                 gGlobalAggRx,
                 reductionRatio,
                 gGlobalDirectAggRx,
                 gGlobalRelayedAggRx,
                 gGlobalRelayForward);
        lines.push_back(buf);
        snprintf(buf, sizeof(buf), "RawDroppedCum=%lu", gRawDroppedCum);
        lines.push_back(buf);
        PrintBox("DELIVERY & AGGREGATION SUMMARY", lines);
    }

    {
        std::vector<std::string> lines;
        char buf[256];
        snprintf(buf,
                 sizeof(buf),
                 "Failures=%u (CH12 at t=%.1fs) Recovery=%s recoveredClusters=%u delay=%.1fs",
                 gGlobalFailedChCount,
                 gFailureTimeSec,
                 gEnableRecovery ? "ON" : "OFF",
                 gGlobalRecoveredClusterCount,
                 gRecoveryDelaySec);
        lines.push_back(buf);
        for (uint32_t cid = 0; cid < kClusters; ++cid)
        {
            snprintf(buf,
                     sizeof(buf),
                     "Cluster%u disconnectedSeconds=%.1f rawDropped=%lu",
                     cid,
                     gClusterDisconnectedSeconds[cid],
                     gClusterRawDroppedCum[cid]);
            lines.push_back(buf);
        }
        PrintBox("FAILURE & RECOVERY SUMMARY", lines);
    }

    {
        const EnergySnapshot es = GetEnergySnapshot();
        const EnergyPercentiles p = ComputeEnergyPercentiles();
        std::vector<std::string> lines;
        char buf[256];
        snprintf(buf, sizeof(buf), "avg=%.3fJ min=%.3fJ max=%.3fJ", es.avgResidualJ, p.minVal, p.maxVal);
        lines.push_back(buf);
        snprintf(buf, sizeof(buf), "p5=%.3fJ p50=%.3fJ p95=%.3fJ", p.p5, p.p50, p.p95);
        lines.push_back(buf);
        snprintf(buf,
                 sizeof(buf),
                 "lowThreshold=%.3fJ (initial=%.3fJ * frac=%.2f) lowCount=%u totalConsumed=%.3fJ",
                 LowEnergyThresholdJ(),
                 gInitialEnergyJ,
                 gLowEnergyFrac,
                 es.lowEnergyNodes,
                 es.totalConsumedJ);
        lines.push_back(buf);
        PrintBox("ENERGY DISTRIBUTION", lines);
    }

    {
        std::vector<std::string> lines;
        char buf[256];
        const auto topK = GetTopKLowestEnergy(gTopK);
        snprintf(buf, sizeof(buf), "%-6s %-6s %-7s %-9s %-9s", "Node", "Role", "Cluster", "ResidualJ", "ConsumedJ");
        lines.push_back(buf);
        for (const auto& n : topK)
        {
            snprintf(buf, sizeof(buf), "%-6u %-6s %-7d %-9.3f %-9.3f", n.nodeId, n.role.c_str(), n.clusterId, n.residualJ, n.consumedJ);
            lines.push_back(buf);
        }
        PrintBox("TOP-K LOWEST RESIDUAL ENERGY", lines);
    }

    {
        std::vector<std::string> lines;
        char buf[256];
        const auto topK = GetTopKHighestConsumed(gTopK);
        snprintf(buf, sizeof(buf), "%-6s %-6s %-7s %-9s %-9s", "Node", "Role", "Cluster", "ConsumedJ", "ResidualJ");
        lines.push_back(buf);
        for (const auto& n : topK)
        {
            snprintf(buf, sizeof(buf), "%-6u %-6s %-7d %-9.3f %-9.3f", n.nodeId, n.role.c_str(), n.clusterId, n.consumedJ, n.residualJ);
            lines.push_back(buf);
        }
        PrintBox("TOP-K HIGHEST CONSUMED", lines);
    }

    {
        std::vector<std::string> lines;
        char buf[256];
        snprintf(buf, sizeof(buf), "%-3s %-10s %-6s %-8s %-10s %-8s %-8s %-9s %-10s", "CID", "Status", "OrigCH", "ActiveCH", "Mode", "CHResJ", "AvgMemJ", "ConsumedJ", "DiscSec");
        lines.push_back(buf);
        for (const auto& def : gClusterDefs)
        {
            const uint32_t activeCh = gClusterCurrentCh[def.clusterId];
            double memberResidualSum = 0.0;
            for (uint32_t memberId : def.members)
            {
                memberResidualSum += gResidualEnergyJ[memberId];
            }
            const double avgMemberResidual = def.members.empty() ? 0.0 : (memberResidualSum / static_cast<double>(def.members.size()));
            double clusterConsumed = 0.0;
            clusterConsumed += gConsumedEnergyJ[def.chId];
            for (uint32_t memberId : def.members)
            {
                clusterConsumed += gConsumedEnergyJ[memberId];
            }
            snprintf(buf,
                     sizeof(buf),
                     "%-3u %-10s %-6u %-8u %-10s %-8.3f %-8.3f %-9.3f %-10.1f",
                     def.clusterId,
                     ClusterHealthString(def.clusterId).c_str(),
                     def.chId,
                     activeCh,
                     ClusterModeString(def.clusterId).c_str(),
                     gResidualEnergyJ[activeCh],
                     avgMemberResidual,
                     clusterConsumed,
                     gClusterDisconnectedSeconds[def.clusterId]);
            lines.push_back(buf);
        }
        PrintBox("CLUSTER SUMMARY", lines);
    }

    if (!gExportNodeEnergyCsv.empty())
    {
        ExportNodeEnergyCsv(gExportNodeEnergyCsv);
    }
    if (!gExportEventsCsv.empty())
    {
        ExportEventsCsv(gExportEventsCsv);
    }

    ExportRunFiles();

    Simulator::Destroy();
    return 0;
}
