#include "ns3/applications-module.h"
#include "ns3/core-module.h"
#include "ns3/energy-module.h"
#include "ns3/flow-monitor-module.h"
#include "ns3/internet-module.h"
#include "ns3/mobility-module.h"
#include "ns3/netanim-module.h"
#include "ns3/network-module.h"
#include "ns3/wifi-module.h"

#include <algorithm>
#include <cctype>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <limits>
#include <map>
#include <memory>
#include <set>
#include <sstream>
#include <string>
#include <vector>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("TestNs3Leach");

namespace
{

struct LeachConfig
{
    uint32_t nNodes = 100;
    double areaX = 100.0;
    double areaY = 100.0;
    double sinkX = 50.0;
    double sinkY = 150.0;
    double initialEnergy = 2.0;
    double chProbability = 0.05;
    uint32_t packetSize = 200;
    uint32_t rounds = 100;
    double roundDuration = 10.0;
    double setupDuration = 2.0;
    double dataInterval = 0.0;
    uint32_t slotsPerRound = 0;
    double txRange = 200.0;
    bool enableFlowMonitor = false;
    bool enableNetAnim = false;
    uint32_t run = 1;
    uint32_t seed = 1;
    std::string outputTag;

    uint16_t memberPort = 9000;
    uint16_t sinkPort = 9001;
    double supplyVoltage = 3.0;
    double txCurrentA = 0.0174;
    double rxCurrentA = 0.0197;
    double idleCurrentA = 0.000426;
    double sleepCurrentA = 0.0000142;
    double aggregationEnergyPerBitJ = 5e-9;

    double
    GetSteadyStateDuration() const
    {
        return std::max(0.0, roundDuration - setupDuration);
    }
};

struct LeachNodeState
{
    uint32_t nodeId = 0;
    bool alive = true;
    bool isClusterHead = false;
    int32_t clusterHeadId = -1;
    uint32_t timesSelectedAsCh = 0;
    int32_t roundLastBecameCh = -1;
    uint64_t packetsSent = 0;
    uint64_t packetsReceived = 0;
    uint32_t tdmaSlot = 0;
    double aggregationEnergySpentJ = 0.0;
    double residualEnergyJ = 0.0;
};

struct RoundStats
{
    uint32_t round = 0;
    uint32_t alive = 0;
    uint32_t dead = 0;
    uint32_t clusterHeads = 0;
    uint64_t packetsGenerated = 0;
    uint64_t packetsToCh = 0;
    uint64_t packetsToSink = 0;
    uint64_t actualSinkPackets = 0;
    double pdr = 0.0;
    double totalResidualEnergy = 0.0;
    double avgResidualEnergy = 0.0;
    double roundEnergyConsumed = 0.0;
    double cumulativeEnergyConsumed = 0.0;
    double startEnergy = 0.0;
    std::set<uint32_t> memberSeqsReceived;
    std::set<uint32_t> sinkSeqsReceived;
    std::map<uint32_t, uint32_t> reportsReceivedByCh;
};

enum PacketKind : uint8_t
{
    MEMBER_DATA = 1,
    AGGREGATED_DATA = 2
};

class LeachPacketHeader : public Header
{
  public:
    LeachPacketHeader() = default;

    static TypeId
    GetTypeId()
    {
        static TypeId tid =
            TypeId("ns3::LeachPacketHeader").SetParent<Header>().AddConstructor<LeachPacketHeader>();
        return tid;
    }

    TypeId
    GetInstanceTypeId() const override
    {
        return GetTypeId();
    }

    void
    SetPacketKind(uint8_t kind)
    {
        m_kind = kind;
    }

    void
    SetRound(uint16_t round)
    {
        m_round = round;
    }

    void
    SetSourceId(uint16_t nodeId)
    {
        m_sourceId = nodeId;
    }

    void
    SetDestinationId(uint16_t nodeId)
    {
        m_destinationId = nodeId;
    }

    void
    SetSequence(uint32_t sequence)
    {
        m_sequence = sequence;
    }

    void
    SetReportCount(uint16_t reportCount)
    {
        m_reportCount = reportCount;
    }

    void
    SetPayloadBytes(uint16_t payloadBytes)
    {
        m_payloadBytes = payloadBytes;
    }

    void
    SetClusterId(uint16_t clusterId)
    {
        m_clusterId = clusterId;
    }

    uint8_t
    GetPacketKind() const
    {
        return m_kind;
    }

    uint16_t
    GetRound() const
    {
        return m_round;
    }

    uint16_t
    GetSourceId() const
    {
        return m_sourceId;
    }

    uint16_t
    GetDestinationId() const
    {
        return m_destinationId;
    }

    uint32_t
    GetSequence() const
    {
        return m_sequence;
    }

    uint16_t
    GetReportCount() const
    {
        return m_reportCount;
    }

    uint16_t
    GetPayloadBytes() const
    {
        return m_payloadBytes;
    }

    uint16_t
    GetClusterId() const
    {
        return m_clusterId;
    }

    uint32_t
    GetSerializedSize() const override
    {
        return 17;
    }

    void
    Serialize(Buffer::Iterator start) const override
    {
        start.WriteU8(m_kind);
        start.WriteHtonU16(m_round);
        start.WriteHtonU16(m_sourceId);
        start.WriteHtonU16(m_destinationId);
        start.WriteHtonU32(m_sequence);
        start.WriteHtonU16(m_reportCount);
        start.WriteHtonU16(m_payloadBytes);
        start.WriteHtonU16(m_clusterId);
    }

    uint32_t
    Deserialize(Buffer::Iterator start) override
    {
        m_kind = start.ReadU8();
        m_round = start.ReadNtohU16();
        m_sourceId = start.ReadNtohU16();
        m_destinationId = start.ReadNtohU16();
        m_sequence = start.ReadNtohU32();
        m_reportCount = start.ReadNtohU16();
        m_payloadBytes = start.ReadNtohU16();
        m_clusterId = start.ReadNtohU16();
        return GetSerializedSize();
    }

    void
    Print(std::ostream& os) const override
    {
        os << "kind=" << static_cast<uint32_t>(m_kind) << " round=" << m_round
           << " src=" << m_sourceId << " dst=" << m_destinationId << " seq=" << m_sequence
           << " reports=" << m_reportCount << " payloadBytes=" << m_payloadBytes
           << " clusterId=" << m_clusterId;
    }

  private:
    uint8_t m_kind = MEMBER_DATA;
    uint16_t m_round = 0;
    uint16_t m_sourceId = 0;
    uint16_t m_destinationId = 0;
    uint32_t m_sequence = 0;
    uint16_t m_reportCount = 0;
    uint16_t m_payloadBytes = 0;
    uint16_t m_clusterId = 0;
};

class LeachController;

class SensorReceiverApp : public Application
{
  public:
    void
    Setup(uint32_t nodeId, LeachController* controller, uint16_t port)
    {
        m_nodeId = nodeId;
        m_controller = controller;
        m_port = port;
    }

  private:
    void StartApplication() override;
    void StopApplication() override;
    void HandleRead(Ptr<Socket> socket);

    uint32_t m_nodeId = 0;
    LeachController* m_controller = nullptr;
    uint16_t m_port = 0;
    Ptr<Socket> m_socket;
};

class SinkReceiverApp : public Application
{
  public:
    void
    Setup(LeachController* controller, uint16_t port)
    {
        m_controller = controller;
        m_port = port;
    }

  private:
    void StartApplication() override;
    void StopApplication() override;
    void HandleRead(Ptr<Socket> socket);

    LeachController* m_controller = nullptr;
    uint16_t m_port = 0;
    Ptr<Socket> m_socket;
};

class LeachController
{
  public:
    explicit LeachController(LeachConfig config)
        : m_config(std::move(config))
    {
        m_roundStats.resize(m_config.rounds);
        for (uint32_t round = 0; round < m_config.rounds; ++round)
        {
            m_roundStats[round].round = round;
        }
    }

    ~LeachController()
    {
        if (m_anim != nullptr)
        {
            delete m_anim;
            m_anim = nullptr;
        }
    }

    void
    Initialize()
    {
        ValidateConfig();
        RngSeedManager::SetSeed(m_config.seed);
        RngSeedManager::SetRun(m_config.run);

        m_uniformRv = CreateObject<UniformRandomVariable>();
        m_uniformRv->SetAttribute("Min", DoubleValue(0.0));
        m_uniformRv->SetAttribute("Max", DoubleValue(1.0));

        CreateResultsDirectory();
        OpenOutputFiles();
        CreateNodes();
        ConfigureMobility();
        ConfigureWifi();
        InstallInternetStack();
        ConfigureEnergy();
        InstallApplications();
        ConfigureAnimation();
        ConfigureFlowMonitor();

        for (uint32_t nodeId = 0; nodeId < m_config.nNodes; ++nodeId)
        {
            RefreshNodeEnergy(nodeId);
        }

        ScheduleRounds();
    }

    void
    Finalize()
    {
        RefreshAllNodeEnergy();

        if (m_flowMonitor != nullptr)
        {
            m_flowMonitor->CheckForLostPackets();
            const auto path = (std::filesystem::path(m_resultsDir) / "flowmon.xml").string();
            m_flowMonitor->SerializeToXmlFile(path, true, true);
        }

        WriteSummary();
        CloseOutputFiles();

        if (m_anim != nullptr)
        {
            delete m_anim;
            m_anim = nullptr;
        }

        std::cout << "LEACH results directory: " << m_resultsDir << std::endl;
    }

    void
    StartRound(uint32_t round)
    {
        if (round >= m_config.rounds)
        {
            return;
        }

        RefreshAllNodeEnergy();
        ResetRoundState(round);

        if (m_roundStats[round].alive == 0)
        {
            return;
        }

        const double setupSpan = std::max(0.0, m_config.setupDuration);

        ElectClusterHeads(round);
        Simulator::Schedule(Seconds(std::min(0.2 * setupSpan, setupSpan)),
                            &LeachController::AdvertiseClusterHeads,
                            this,
                            round);
        Simulator::Schedule(Seconds(std::min(0.5 * setupSpan, setupSpan)),
                            &LeachController::FormClusters,
                            this,
                            round);
        Simulator::Schedule(Seconds(std::min(0.8 * setupSpan, setupSpan)),
                            &LeachController::AssignTdmaSlots,
                            this,
                            round);
        Simulator::Schedule(Seconds(m_config.setupDuration),
                            &LeachController::StartSteadyState,
                            this,
                            round);
    }

    void
    FinishRound(uint32_t round)
    {
        if (round >= m_config.rounds)
        {
            return;
        }

        RefreshAllNodeEnergy();

        RoundStats& stats = m_roundStats[round];
        stats.alive = CountAliveNodes();
        stats.dead = m_config.nNodes - stats.alive;
        stats.totalResidualEnergy = GetTotalResidualEnergy();
        stats.avgResidualEnergy =
            (m_config.nNodes > 0) ? (stats.totalResidualEnergy / static_cast<double>(m_config.nNodes))
                                  : 0.0;
        stats.roundEnergyConsumed = std::max(0.0, stats.startEnergy - stats.totalResidualEnergy);
        m_cumulativeEnergyConsumed += stats.roundEnergyConsumed;
        stats.cumulativeEnergyConsumed = m_cumulativeEnergyConsumed;
        stats.pdr = (stats.packetsGenerated > 0)
                        ? static_cast<double>(stats.packetsToSink) /
                              static_cast<double>(stats.packetsGenerated)
                        : 0.0;

        UpdateMortalityMilestones(round, stats.dead);
        WriteMetrics(round);
        WriteNodeEnergy(round);
        m_completedRounds = round + 1;
    }

    void
    HandleSensorPacket(uint32_t receiverId, Ptr<Packet> packet, const Address& from)
    {
        if (receiverId >= m_config.nNodes || packet == nullptr || packet->GetSize() == 0)
        {
            return;
        }

        LeachPacketHeader header;
        packet->RemoveHeader(header);

        if (header.GetPacketKind() != MEMBER_DATA)
        {
            return;
        }

        const uint32_t round = header.GetRound();
        if (round >= m_config.rounds)
        {
            return;
        }

        RefreshNodeEnergy(receiverId);

        if (!m_states[receiverId].alive || !m_states[receiverId].isClusterHead)
        {
            return;
        }

        const uint32_t senderId = header.GetSourceId();
        if (senderId >= m_config.nNodes || !m_states[senderId].alive)
        {
            return;
        }

        auto memberToChIt = m_memberToCh.find(senderId);
        if (memberToChIt == m_memberToCh.end() || memberToChIt->second != receiverId)
        {
            return;
        }

        RoundStats& stats = m_roundStats[round];
        if (!stats.memberSeqsReceived.insert(header.GetSequence()).second)
        {
            return;
        }

        stats.packetsToCh += header.GetReportCount();
        stats.reportsReceivedByCh[receiverId] += header.GetReportCount();
        m_states[receiverId].packetsReceived += header.GetReportCount();

        const Ipv4Address fromIp = InetSocketAddress::ConvertFrom(from).GetIpv4();
        std::ostringstream event;
        event << "recv_ch";
        LogPacketEvent(round,
                       event.str(),
                       senderId,
                       receiverId,
                       header,
                       packet->GetSize(),
                       fromIp,
                       m_interfaces.GetAddress(receiverId));
    }

    void
    HandleSinkPacket(Ptr<Packet> packet, const Address& from)
    {
        if (packet == nullptr || packet->GetSize() == 0)
        {
            return;
        }

        LeachPacketHeader header;
        packet->RemoveHeader(header);

        if (header.GetPacketKind() != AGGREGATED_DATA)
        {
            return;
        }

        const uint32_t round = header.GetRound();
        if (round >= m_config.rounds)
        {
            return;
        }

        RoundStats& stats = m_roundStats[round];
        if (!stats.sinkSeqsReceived.insert(header.GetSequence()).second)
        {
            return;
        }

        stats.actualSinkPackets += 1;
        stats.packetsToSink += header.GetReportCount();
        m_totalActualPacketsReceivedAtSink += 1;
        m_totalLogicalReportsAtSink += header.GetReportCount();

        const Ipv4Address fromIp = InetSocketAddress::ConvertFrom(from).GetIpv4();
        std::ostringstream event;
        event << "recv_sink";
        LogPacketEvent(round,
                       event.str(),
                       header.GetSourceId(),
                       m_config.nNodes,
                       header,
                       packet->GetSize(),
                       fromIp,
                       m_interfaces.GetAddress(m_config.nNodes));
    }

    std::string
    GetResultsDir() const
    {
        return m_resultsDir;
    }

  private:
    void
    ValidateConfig() const
    {
        NS_ABORT_MSG_IF(m_config.nNodes == 0, "nNodes must be > 0");
        NS_ABORT_MSG_IF(m_config.rounds == 0, "rounds must be > 0");
        NS_ABORT_MSG_IF(m_config.packetSize == 0, "packetSize must be > 0");
        NS_ABORT_MSG_IF(m_config.chProbability <= 0.0 || m_config.chProbability > 1.0,
                        "chProbability must be in (0, 1]");
        NS_ABORT_MSG_IF(m_config.roundDuration <= 0.0, "roundDuration must be > 0");
        NS_ABORT_MSG_IF(m_config.setupDuration < 0.0, "setupDuration must be >= 0");
        NS_ABORT_MSG_IF(m_config.setupDuration >= m_config.roundDuration,
                        "setupDuration must be < roundDuration");
        NS_ABORT_MSG_IF(m_config.initialEnergy <= 0.0, "initialEnergy must be > 0");
        NS_ABORT_MSG_IF(m_config.areaX <= 0.0 || m_config.areaY <= 0.0,
                        "areaX and areaY must be > 0");
        NS_ABORT_MSG_IF(m_config.txRange <= 0.0, "txRange must be > 0");
    }

    void
    CreateResultsDirectory()
    {
        auto timestamp = BuildTimestamp();
        std::string folder = "test_ns3_leach_";
        if (!m_config.outputTag.empty())
        {
            folder += SanitizeTag(m_config.outputTag) + "_";
        }
        folder += timestamp;

        std::filesystem::path resultsBase("results");
        std::filesystem::create_directories(resultsBase);
        m_resultsDir = (resultsBase / folder).string();
        std::filesystem::create_directories(m_resultsDir);
    }

    void
    OpenOutputFiles()
    {
        const std::filesystem::path base(m_resultsDir);

        m_metricsFile.open(base / "metrics.csv", std::ios::out | std::ios::trunc);
        m_clusterHistoryFile.open(base / "cluster_history.csv", std::ios::out | std::ios::trunc);
        m_nodeEnergyFile.open(base / "node_energy.csv", std::ios::out | std::ios::trunc);
        m_packetsFile.open(base / "packets.csv", std::ios::out | std::ios::trunc);

        m_metricsFile << "round,alive,dead,cluster_heads,packets_generated,packets_to_ch,"
                         "packets_to_sink,pdr,total_residual_energy,avg_residual_energy,"
                         "round_energy_consumed,cumulative_energy_consumed\n";
        m_clusterHistoryFile << "round,node_id,is_cluster_head,cluster_id\n";
        m_nodeEnergyFile << "round,node_id,alive,residual_energy\n";
        m_packetsFile << "time,round,event,src,dst,message_type,sequence,report_count,bytes,"
                         "src_ip,dst_ip\n";
    }

    void
    CloseOutputFiles()
    {
        if (m_metricsFile.is_open())
        {
            m_metricsFile.close();
        }
        if (m_clusterHistoryFile.is_open())
        {
            m_clusterHistoryFile.close();
        }
        if (m_nodeEnergyFile.is_open())
        {
            m_nodeEnergyFile.close();
        }
        if (m_packetsFile.is_open())
        {
            m_packetsFile.close();
        }
    }

    void
    CreateNodes()
    {
        m_sensorNodes.Create(m_config.nNodes);

        NodeContainer sinkContainer;
        sinkContainer.Create(1);
        m_sinkNode = sinkContainer.Get(0);

        m_allNodes.Add(m_sensorNodes);
        m_allNodes.Add(sinkContainer);

        m_states.resize(m_config.nNodes);
        m_txSockets.resize(m_config.nNodes);

        for (uint32_t nodeId = 0; nodeId < m_config.nNodes; ++nodeId)
        {
            m_states[nodeId].nodeId = nodeId;
            m_states[nodeId].residualEnergyJ = m_config.initialEnergy;
        }
    }

    void
    ConfigureMobility()
    {
        Ptr<ListPositionAllocator> allocator = CreateObject<ListPositionAllocator>();
        Ptr<UniformRandomVariable> xRv = CreateObject<UniformRandomVariable>();
        Ptr<UniformRandomVariable> yRv = CreateObject<UniformRandomVariable>();
        xRv->SetAttribute("Min", DoubleValue(0.0));
        xRv->SetAttribute("Max", DoubleValue(m_config.areaX));
        yRv->SetAttribute("Min", DoubleValue(0.0));
        yRv->SetAttribute("Max", DoubleValue(m_config.areaY));

        for (uint32_t nodeId = 0; nodeId < m_config.nNodes; ++nodeId)
        {
            allocator->Add(Vector(xRv->GetValue(), yRv->GetValue(), 0.0));
        }
        allocator->Add(Vector(m_config.sinkX, m_config.sinkY, 0.0));

        MobilityHelper mobility;
        mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
        mobility.SetPositionAllocator(allocator);
        mobility.Install(m_allNodes);
    }

    void
    ConfigureWifi()
    {
        YansWifiChannelHelper channel;
        channel.SetPropagationDelay("ns3::ConstantSpeedPropagationDelayModel");
        channel.AddPropagationLoss("ns3::RangePropagationLossModel",
                                   "MaxRange",
                                   DoubleValue(m_config.txRange));

        YansWifiPhyHelper phy;
        phy.SetChannel(channel.Create());
        phy.Set("TxPowerStart", DoubleValue(0.0));
        phy.Set("TxPowerEnd", DoubleValue(0.0));

        WifiHelper wifi;
        wifi.SetStandard(WIFI_STANDARD_80211b);
        wifi.SetRemoteStationManager("ns3::ConstantRateWifiManager",
                                     "DataMode",
                                     StringValue("DsssRate1Mbps"),
                                     "ControlMode",
                                     StringValue("DsssRate1Mbps"));

        WifiMacHelper mac;
        mac.SetType("ns3::AdhocWifiMac");

        m_allDevices = wifi.Install(phy, mac, m_allNodes);
        for (uint32_t nodeId = 0; nodeId < m_config.nNodes; ++nodeId)
        {
            m_sensorDevices.Add(m_allDevices.Get(nodeId));
        }
    }

    void
    InstallInternetStack()
    {
        InternetStackHelper internet;
        internet.Install(m_allNodes);

        Ipv4AddressHelper address;
        address.SetBase("10.1.0.0", "255.255.0.0");
        m_interfaces = address.Assign(m_allDevices);
    }

    void
    ConfigureEnergy()
    {
        BasicEnergySourceHelper sourceHelper;
        sourceHelper.Set("BasicEnergySourceInitialEnergyJ", DoubleValue(m_config.initialEnergy));
        sourceHelper.Set("BasicEnergySupplyVoltageV", DoubleValue(m_config.supplyVoltage));
        sourceHelper.Set("PeriodicEnergyUpdateInterval", TimeValue(MilliSeconds(100)));

        energy::EnergySourceContainer sources = sourceHelper.Install(m_sensorNodes);
        for (uint32_t nodeId = 0; nodeId < sources.GetN(); ++nodeId)
        {
            m_energySources.push_back(DynamicCast<energy::BasicEnergySource>(sources.Get(nodeId)));
        }

        WifiRadioEnergyModelHelper radioEnergyHelper;
        radioEnergyHelper.Set("TxCurrentA", DoubleValue(m_config.txCurrentA));
        radioEnergyHelper.Set("RxCurrentA", DoubleValue(m_config.rxCurrentA));
        radioEnergyHelper.Set("IdleCurrentA", DoubleValue(m_config.idleCurrentA));
        radioEnergyHelper.Set("CcaBusyCurrentA", DoubleValue(m_config.idleCurrentA));
        radioEnergyHelper.Set("SleepCurrentA", DoubleValue(m_config.sleepCurrentA));
        radioEnergyHelper.Install(m_sensorDevices, sources);
    }

    void
    InstallApplications()
    {
        const Time start = Seconds(0.0);
        const Time stop = Seconds(m_config.rounds * m_config.roundDuration + 1.0);

        for (uint32_t nodeId = 0; nodeId < m_config.nNodes; ++nodeId)
        {
            Ptr<SensorReceiverApp> app = CreateObject<SensorReceiverApp>();
            app->Setup(nodeId, this, m_config.memberPort);
            m_sensorNodes.Get(nodeId)->AddApplication(app);
            app->SetStartTime(start);
            app->SetStopTime(stop);
        }

        Ptr<SinkReceiverApp> sinkApp = CreateObject<SinkReceiverApp>();
        sinkApp->Setup(this, m_config.sinkPort);
        m_sinkNode->AddApplication(sinkApp);
        sinkApp->SetStartTime(start);
        sinkApp->SetStopTime(stop);
    }

    void
    ConfigureAnimation()
    {
        if (!m_config.enableNetAnim)
        {
            return;
        }

        const auto path = (std::filesystem::path(m_resultsDir) / "leach-animation.xml").string();
        m_anim = new AnimationInterface(path);
        m_anim->EnablePacketMetadata(true);
        m_anim->UpdateNodeDescription(m_sinkNode, "Sink");
        m_anim->UpdateNodeColor(m_sinkNode, 220, 30, 30);
        m_anim->UpdateNodeSize(m_sinkNode, 14.0, 14.0);

        for (uint32_t nodeId = 0; nodeId < m_config.nNodes; ++nodeId)
        {
            std::ostringstream description;
            description << "N" << nodeId;
            m_anim->UpdateNodeDescription(m_sensorNodes.Get(nodeId), description.str());
            m_anim->UpdateNodeSize(m_sensorNodes.Get(nodeId), 8.0, 8.0);
        }

        UpdateRoleColors();
    }

    void
    ConfigureFlowMonitor()
    {
        if (!m_config.enableFlowMonitor)
        {
            return;
        }

        m_flowMonitorHelper = std::make_unique<FlowMonitorHelper>();
        m_flowMonitor = m_flowMonitorHelper->InstallAll();
    }

    void
    ScheduleRounds()
    {
        for (uint32_t round = 0; round < m_config.rounds; ++round)
        {
            const double roundStart = round * m_config.roundDuration;
            const double roundEnd = roundStart + m_config.roundDuration - 1e-6;
            Simulator::Schedule(Seconds(roundStart), &LeachController::StartRound, this, round);
            Simulator::Schedule(Seconds(roundEnd), &LeachController::FinishRound, this, round);
        }
    }

    void
    ResetRoundState(uint32_t round)
    {
        m_clusters.clear();
        m_memberToCh.clear();

        RoundStats& stats = m_roundStats[round];
        stats.alive = CountAliveNodes();
        stats.dead = m_config.nNodes - stats.alive;
        stats.clusterHeads = 0;
        stats.packetsGenerated = stats.alive;
        stats.packetsToCh = 0;
        stats.packetsToSink = 0;
        stats.actualSinkPackets = 0;
        stats.pdr = 0.0;
        stats.startEnergy = GetTotalResidualEnergy();
        stats.totalResidualEnergy = stats.startEnergy;
        stats.avgResidualEnergy =
            (m_config.nNodes > 0) ? (stats.totalResidualEnergy / static_cast<double>(m_config.nNodes))
                                  : 0.0;
        stats.roundEnergyConsumed = 0.0;
        stats.cumulativeEnergyConsumed = m_cumulativeEnergyConsumed;
        stats.memberSeqsReceived.clear();
        stats.sinkSeqsReceived.clear();
        stats.reportsReceivedByCh.clear();

        m_totalPacketsGenerated += stats.packetsGenerated;

        for (auto& state : m_states)
        {
            state.isClusterHead = false;
            state.clusterHeadId = -1;
            state.tdmaSlot = 0;
        }
    }

    void
    ElectClusterHeads(uint32_t round)
    {
        if (round >= m_config.rounds)
        {
            return;
        }

        const uint32_t epochLength = GetEpochLength();
        std::vector<uint32_t> elected;

        for (uint32_t nodeId = 0; nodeId < m_config.nNodes; ++nodeId)
        {
            RefreshNodeEnergy(nodeId);
            LeachNodeState& state = m_states[nodeId];
            if (!state.alive)
            {
                continue;
            }

            const bool eligible = (state.roundLastBecameCh < 0) ||
                                  (round - static_cast<uint32_t>(state.roundLastBecameCh) >=
                                   epochLength);
            if (!eligible)
            {
                continue;
            }

            const double denominator =
                1.0 - m_config.chProbability * static_cast<double>(round % epochLength);
            const double threshold =
                (denominator > 0.0) ? (m_config.chProbability / denominator) : 1.0;
            if (m_uniformRv->GetValue() <= std::min(1.0, threshold))
            {
                state.isClusterHead = true;
                state.clusterHeadId = static_cast<int32_t>(nodeId);
                state.timesSelectedAsCh += 1;
                state.roundLastBecameCh = static_cast<int32_t>(round);
                elected.push_back(nodeId);
            }
        }

        if (elected.empty())
        {
            const uint32_t forcedNode = ChooseFallbackClusterHead();
            if (forcedNode < m_config.nNodes)
            {
                LeachNodeState& state = m_states[forcedNode];
                state.isClusterHead = true;
                state.clusterHeadId = static_cast<int32_t>(forcedNode);
                state.timesSelectedAsCh += 1;
                state.roundLastBecameCh = static_cast<int32_t>(round);
                elected.push_back(forcedNode);
            }
        }

        for (uint32_t nodeId : elected)
        {
            m_clusters[nodeId] = {};
        }

        m_roundStats[round].clusterHeads = elected.size();
        UpdateRoleColors();
    }

    void
    AdvertiseClusterHeads(uint32_t round)
    {
        if (round >= m_config.rounds)
        {
            return;
        }

        for (const auto& cluster : m_clusters)
        {
            const uint32_t chId = cluster.first;
            if (!m_states[chId].alive)
            {
                continue;
            }
            NS_LOG_INFO("Round " << round << " CH advertisement from node " << chId);
        }
    }

    void
    FormClusters(uint32_t round)
    {
        if (round >= m_config.rounds || m_clusters.empty())
        {
            return;
        }

        for (uint32_t nodeId = 0; nodeId < m_config.nNodes; ++nodeId)
        {
            if (!m_states[nodeId].alive || m_states[nodeId].isClusterHead)
            {
                continue;
            }

            double bestDistance = std::numeric_limits<double>::max();
            int32_t bestCh = -1;

            for (const auto& cluster : m_clusters)
            {
                const uint32_t chId = cluster.first;
                if (!m_states[chId].alive)
                {
                    continue;
                }

                const double distance = GetNodeDistance(nodeId, chId);
                if (distance < bestDistance)
                {
                    bestDistance = distance;
                    bestCh = static_cast<int32_t>(chId);
                }
            }

            if (bestCh >= 0)
            {
                m_states[nodeId].clusterHeadId = bestCh;
                m_memberToCh[nodeId] = static_cast<uint32_t>(bestCh);
                m_clusters[static_cast<uint32_t>(bestCh)].push_back(nodeId);
            }
        }
    }

    void
    AssignTdmaSlots(uint32_t round)
    {
        if (round >= m_config.rounds)
        {
            return;
        }

        for (auto& cluster : m_clusters)
        {
            auto& members = cluster.second;
            std::sort(members.begin(), members.end());
            for (uint32_t index = 0; index < members.size(); ++index)
            {
                m_states[members[index]].tdmaSlot = index;
            }
        }

        WriteClusterHistory(round);
        UpdateRoleColors();
    }

    void
    StartSteadyState(uint32_t round)
    {
        if (round >= m_config.rounds)
        {
            return;
        }

        const double steadyDuration = m_config.GetSteadyStateDuration();

        for (const auto& clusterEntry : m_clusters)
        {
            const uint32_t chId = clusterEntry.first;
            const auto& members = clusterEntry.second;

            if (!RefreshNodeEnergy(chId) || !m_states[chId].alive)
            {
                continue;
            }

            const double slotDuration = ResolveSlotDuration(members.size());
            for (uint32_t slot = 0; slot < members.size(); ++slot)
            {
                const uint32_t memberId = members[slot];
                const double sendDelay = (slot + 0.25) * slotDuration;
                if (sendDelay < m_config.GetSteadyStateDuration() - 0.02)
                {
                    Simulator::Schedule(Seconds(sendDelay),
                                        &LeachController::SendMemberData,
                                        this,
                                        round,
                                        memberId,
                                        chId);
                }
            }

            double chSendDelay = (members.size() + 0.75) * slotDuration;
            const double latest = m_config.GetSteadyStateDuration() - 0.01;
            if (chSendDelay > latest)
            {
                chSendDelay = latest;
            }
            chSendDelay = std::max(chSendDelay, 0.01);

            if (steadyDuration > 0.0)
            {
                Simulator::Schedule(Seconds(chSendDelay),
                                    &LeachController::SendAggregatedData,
                                    this,
                                    round,
                                    chId);
            }
        }
    }

    void
    SendMemberData(uint32_t round, uint32_t memberId, uint32_t chId)
    {
        if (round >= m_config.rounds || memberId >= m_config.nNodes || chId >= m_config.nNodes)
        {
            return;
        }

        if (!RefreshNodeEnergy(memberId) || !RefreshNodeEnergy(chId))
        {
            return;
        }

        if (!m_states[memberId].alive || !m_states[chId].alive || m_states[memberId].isClusterHead)
        {
            return;
        }

        auto memberToChIt = m_memberToCh.find(memberId);
        if (memberToChIt == m_memberToCh.end() || memberToChIt->second != chId)
        {
            return;
        }

        Ptr<Socket> socket = GetOrCreateTxSocket(memberId);
        if (socket == nullptr)
        {
            return;
        }

        LeachPacketHeader header;
        header.SetPacketKind(MEMBER_DATA);
        header.SetRound(static_cast<uint16_t>(round));
        header.SetSourceId(static_cast<uint16_t>(memberId));
        header.SetDestinationId(static_cast<uint16_t>(chId));
        header.SetSequence(static_cast<uint32_t>(m_nextSequence++));
        header.SetReportCount(1);
        header.SetPayloadBytes(static_cast<uint16_t>(m_config.packetSize));
        header.SetClusterId(static_cast<uint16_t>(chId));

        Ptr<Packet> packet = Create<Packet>(m_config.packetSize);
        packet->AddHeader(header);

        const int result = socket->SendTo(packet,
                                          0,
                                          InetSocketAddress(m_interfaces.GetAddress(chId),
                                                            m_config.memberPort));
        if (result < 0)
        {
            return;
        }

        m_states[memberId].packetsSent += 1;
        m_totalActualPacketsSent += 1;

        LogPacketEvent(round,
                       "send_member",
                       memberId,
                       chId,
                       header,
                       packet->GetSize(),
                       m_interfaces.GetAddress(memberId),
                       m_interfaces.GetAddress(chId));
    }

    void
    SendAggregatedData(uint32_t round, uint32_t chId)
    {
        if (round >= m_config.rounds || chId >= m_config.nNodes)
        {
            return;
        }

        if (!RefreshNodeEnergy(chId) || !m_states[chId].alive || !m_states[chId].isClusterHead)
        {
            return;
        }

        const uint32_t reports = 1 + m_roundStats[round].reportsReceivedByCh[chId];
        const double aggregationCost =
            static_cast<double>(reports) * static_cast<double>(m_config.packetSize) * 8.0 *
            m_config.aggregationEnergyPerBitJ;

        m_states[chId].aggregationEnergySpentJ += aggregationCost;
        if (!RefreshNodeEnergy(chId))
        {
            return;
        }

        Ptr<Socket> socket = GetOrCreateTxSocket(chId);
        if (socket == nullptr)
        {
            return;
        }

        LeachPacketHeader header;
        header.SetPacketKind(AGGREGATED_DATA);
        header.SetRound(static_cast<uint16_t>(round));
        header.SetSourceId(static_cast<uint16_t>(chId));
        header.SetDestinationId(static_cast<uint16_t>(m_config.nNodes));
        header.SetSequence(static_cast<uint32_t>(m_nextSequence++));
        header.SetReportCount(static_cast<uint16_t>(reports));
        header.SetPayloadBytes(static_cast<uint16_t>(m_config.packetSize));
        header.SetClusterId(static_cast<uint16_t>(chId));

        Ptr<Packet> packet = Create<Packet>(m_config.packetSize);
        packet->AddHeader(header);

        const int result = socket->SendTo(packet,
                                          0,
                                          InetSocketAddress(m_interfaces.GetAddress(m_config.nNodes),
                                                            m_config.sinkPort));
        if (result < 0)
        {
            return;
        }

        m_states[chId].packetsSent += 1;
        m_totalActualPacketsSent += 1;

        LogPacketEvent(round,
                       "send_sink",
                       chId,
                       m_config.nNodes,
                       header,
                       packet->GetSize(),
                       m_interfaces.GetAddress(chId),
                       m_interfaces.GetAddress(m_config.nNodes));
    }

    Ptr<Socket>
    GetOrCreateTxSocket(uint32_t nodeId)
    {
        if (nodeId >= m_config.nNodes)
        {
            return nullptr;
        }

        if (m_txSockets[nodeId] == nullptr)
        {
            m_txSockets[nodeId] =
                Socket::CreateSocket(m_sensorNodes.Get(nodeId), UdpSocketFactory::GetTypeId());
            m_txSockets[nodeId]->Bind();
            m_txSockets[nodeId]->SetAllowBroadcast(true);
        }
        return m_txSockets[nodeId];
    }

    void
    RefreshAllNodeEnergy()
    {
        for (uint32_t nodeId = 0; nodeId < m_config.nNodes; ++nodeId)
        {
            RefreshNodeEnergy(nodeId);
        }
    }

    bool
    RefreshNodeEnergy(uint32_t nodeId)
    {
        if (nodeId >= m_config.nNodes)
        {
            return false;
        }

        Ptr<energy::BasicEnergySource> source = m_energySources.at(nodeId);
        source->UpdateEnergySource();

        const double actualEnergy = std::max(0.0, source->GetRemainingEnergy());
        const double logicalEnergy =
            std::max(0.0, actualEnergy - m_states[nodeId].aggregationEnergySpentJ);
        m_states[nodeId].residualEnergyJ = logicalEnergy;

        if (logicalEnergy <= 1e-9 || actualEnergy <= 1e-9)
        {
            MarkNodeDead(nodeId);
            return false;
        }

        return true;
    }

    void
    MarkNodeDead(uint32_t nodeId)
    {
        if (nodeId >= m_config.nNodes || !m_states[nodeId].alive)
        {
            return;
        }

        m_states[nodeId].alive = false;
        m_states[nodeId].isClusterHead = false;
        m_states[nodeId].clusterHeadId = -1;
        m_states[nodeId].residualEnergyJ = 0.0;

        if (m_anim != nullptr)
        {
            m_anim->UpdateNodeColor(m_sensorNodes.Get(nodeId), 110, 110, 110);
        }
    }

    double
    GetTotalResidualEnergy() const
    {
        double total = 0.0;
        for (const auto& state : m_states)
        {
            total += state.residualEnergyJ;
        }
        return total;
    }

    uint32_t
    CountAliveNodes() const
    {
        uint32_t alive = 0;
        for (const auto& state : m_states)
        {
            if (state.alive)
            {
                ++alive;
            }
        }
        return alive;
    }

    uint32_t
    GetEpochLength() const
    {
        return std::max(1u, static_cast<uint32_t>(std::lround(1.0 / m_config.chProbability)));
    }

    uint32_t
    ChooseFallbackClusterHead() const
    {
        uint32_t bestNode = m_config.nNodes;
        double bestEnergy = -1.0;
        double bestDistance = std::numeric_limits<double>::max();

        for (uint32_t nodeId = 0; nodeId < m_config.nNodes; ++nodeId)
        {
            const auto& state = m_states[nodeId];
            if (!state.alive)
            {
                continue;
            }

            const double energy = state.residualEnergyJ;
            const double distance = GetDistanceToSink(nodeId);
            const bool betterEnergy = energy > bestEnergy + 1e-12;
            const bool betterDistance =
                std::abs(energy - bestEnergy) <= 1e-12 && distance < bestDistance;
            const bool betterId = std::abs(energy - bestEnergy) <= 1e-12 &&
                                  std::abs(distance - bestDistance) <= 1e-12 && nodeId < bestNode;

            if (betterEnergy || betterDistance || betterId)
            {
                bestNode = nodeId;
                bestEnergy = energy;
                bestDistance = distance;
            }
        }

        return bestNode;
    }

    double
    ResolveSlotDuration(uint32_t memberCount) const
    {
        const double steady = m_config.GetSteadyStateDuration();
        const uint32_t slotsNeeded = std::max(1u, memberCount + 1u);
        const double maxPerCluster = steady / static_cast<double>(slotsNeeded);

        if (m_config.dataInterval > 0.0)
        {
            return std::max(0.001, std::min(m_config.dataInterval, maxPerCluster));
        }
        if (m_config.slotsPerRound > 0)
        {
            return std::max(0.001,
                            std::min(steady / static_cast<double>(m_config.slotsPerRound),
                                     maxPerCluster));
        }
        return std::max(0.001, maxPerCluster);
    }

    void
    UpdateRoleColors()
    {
        if (m_anim == nullptr)
        {
            return;
        }

        for (uint32_t nodeId = 0; nodeId < m_config.nNodes; ++nodeId)
        {
            if (!m_states[nodeId].alive)
            {
                m_anim->UpdateNodeColor(m_sensorNodes.Get(nodeId), 110, 110, 110);
            }
            else if (m_states[nodeId].isClusterHead)
            {
                m_anim->UpdateNodeColor(m_sensorNodes.Get(nodeId), 255, 140, 0);
            }
            else
            {
                m_anim->UpdateNodeColor(m_sensorNodes.Get(nodeId), 0, 170, 90);
            }
        }
    }

    void
    WriteMetrics(uint32_t round)
    {
        const RoundStats& stats = m_roundStats.at(round);
        m_metricsFile << round << ',' << stats.alive << ',' << stats.dead << ','
                      << stats.clusterHeads << ',' << stats.packetsGenerated << ','
                      << stats.packetsToCh << ',' << stats.packetsToSink << ','
                      << FormatDouble(stats.pdr) << ',' << FormatDouble(stats.totalResidualEnergy)
                      << ',' << FormatDouble(stats.avgResidualEnergy) << ','
                      << FormatDouble(stats.roundEnergyConsumed) << ','
                      << FormatDouble(stats.cumulativeEnergyConsumed) << '\n';
    }

    void
    WriteClusterHistory(uint32_t round)
    {
        for (uint32_t nodeId = 0; nodeId < m_config.nNodes; ++nodeId)
        {
            const auto& state = m_states[nodeId];
            const int32_t clusterId = state.isClusterHead
                                          ? static_cast<int32_t>(nodeId)
                                          : (state.clusterHeadId >= 0 ? state.clusterHeadId : -1);
            m_clusterHistoryFile << round << ',' << nodeId << ','
                                 << (state.isClusterHead ? 1 : 0) << ',' << clusterId << '\n';
        }
    }

    void
    WriteNodeEnergy(uint32_t round)
    {
        for (uint32_t nodeId = 0; nodeId < m_config.nNodes; ++nodeId)
        {
            const auto& state = m_states[nodeId];
            m_nodeEnergyFile << round << ',' << nodeId << ',' << (state.alive ? 1 : 0) << ','
                             << FormatDouble(state.residualEnergyJ) << '\n';
        }
    }

    void
    LogPacketEvent(uint32_t round,
                   const std::string& event,
                   uint32_t src,
                   uint32_t dst,
                   const LeachPacketHeader& header,
                   uint32_t bytes,
                   const Ipv4Address& srcIp,
                   const Ipv4Address& dstIp)
    {
        m_packetsFile << FormatDouble(Simulator::Now().GetSeconds()) << ',' << round << ','
                      << event << ',' << src << ',' << dst << ','
                      << static_cast<uint32_t>(header.GetPacketKind()) << ','
                      << header.GetSequence() << ',' << header.GetReportCount() << ',' << bytes
                      << ',' << srcIp << ',' << dstIp << '\n';
    }

    void
    UpdateMortalityMilestones(uint32_t round, uint32_t deadCount)
    {
        if (deadCount > 0 && m_firstNodeDeathRound < 0)
        {
            m_firstNodeDeathRound = static_cast<int32_t>(round);
        }

        if (deadCount >= static_cast<uint32_t>(std::ceil(m_config.nNodes / 2.0)) &&
            m_halfNodesDeadRound < 0)
        {
            m_halfNodesDeadRound = static_cast<int32_t>(round);
        }

        if (deadCount == m_config.nNodes)
        {
            m_lastNodeDeathRound = static_cast<int32_t>(round);
        }
    }

    void
    WriteSummary() const
    {
        std::ofstream summary(std::filesystem::path(m_resultsDir) / "summary.txt",
                              std::ios::out | std::ios::trunc);

        const uint32_t alive = CountAliveNodes();
        const uint32_t dead = m_config.nNodes - alive;
        const double totalResidualEnergy = GetTotalResidualEnergy();

        summary << "LEACH NS-3 Simulation Summary\n";
        summary << "============================\n\n";
        summary << "Simulation parameters\n";
        summary << "nNodes=" << m_config.nNodes << '\n';
        summary << "areaX=" << m_config.areaX << '\n';
        summary << "areaY=" << m_config.areaY << '\n';
        summary << "sinkX=" << m_config.sinkX << '\n';
        summary << "sinkY=" << m_config.sinkY << '\n';
        summary << "initialEnergy=" << m_config.initialEnergy << '\n';
        summary << "chProbability=" << m_config.chProbability << '\n';
        summary << "packetSize=" << m_config.packetSize << '\n';
        summary << "rounds=" << m_config.rounds << '\n';
        summary << "roundDuration=" << m_config.roundDuration << '\n';
        summary << "setupDuration=" << m_config.setupDuration << '\n';
        summary << "dataInterval=" << m_config.dataInterval << '\n';
        summary << "slotsPerRound=" << m_config.slotsPerRound << '\n';
        summary << "txRange=" << m_config.txRange << '\n';
        summary << "enableFlowMonitor=" << (m_config.enableFlowMonitor ? 1 : 0) << '\n';
        summary << "enableNetAnim=" << (m_config.enableNetAnim ? 1 : 0) << '\n';
        summary << "seed=" << m_config.seed << '\n';
        summary << "run=" << m_config.run << "\n\n";
        summary << "Results\n";
        summary << "total rounds completed=" << m_completedRounds << '\n';
        summary << "total packets sent=" << m_totalActualPacketsSent << '\n';
        summary << "total packets received at sink=" << m_totalActualPacketsReceivedAtSink << '\n';
        summary << "total logical reports received at sink=" << m_totalLogicalReportsAtSink << '\n';
        summary << "first node death round=" << m_firstNodeDeathRound << '\n';
        summary << "half nodes dead round=" << m_halfNodesDeadRound << '\n';
        summary << "last node death round=" << m_lastNodeDeathRound << '\n';
        summary << "final alive count=" << alive << '\n';
        summary << "final dead count=" << dead << '\n';
        summary << "final total residual energy=" << FormatDouble(totalResidualEnergy) << '\n';
        summary << "output directory path=" << m_resultsDir << '\n';
    }

    static std::string
    FormatDouble(double value)
    {
        std::ostringstream out;
        out << std::fixed << std::setprecision(6) << value;
        return out.str();
    }

    std::string
    BuildTimestamp() const
    {
        const auto now = std::chrono::system_clock::now();
        const auto tt = std::chrono::system_clock::to_time_t(now);
        const auto ms =
            std::chrono::duration_cast<std::chrono::milliseconds>(now.time_since_epoch()) % 1000;
        std::tm tm{};
        localtime_r(&tt, &tm);

        char buffer[64];
        std::strftime(buffer, sizeof(buffer), "%Y%m%d_%H%M%S", &tm);

        std::ostringstream out;
        out << buffer << '_' << std::setw(3) << std::setfill('0') << ms.count();
        return out.str();
    }

    std::string
    SanitizeTag(std::string tag) const
    {
        for (char& c : tag)
        {
            if (!std::isalnum(static_cast<unsigned char>(c)) && c != '-' && c != '_')
            {
                c = '_';
            }
        }
        return tag;
    }

    Vector
    GetPosition(Ptr<Node> node) const
    {
        return node->GetObject<MobilityModel>()->GetPosition();
    }

    double
    GetNodeDistance(uint32_t nodeA, uint32_t nodeB) const
    {
        const Vector a = GetPosition(m_sensorNodes.Get(nodeA));
        const Vector b = GetPosition(m_sensorNodes.Get(nodeB));
        return CalculateDistance(a, b);
    }

    double
    GetDistanceToSink(uint32_t nodeId) const
    {
        const Vector nodePos = GetPosition(m_sensorNodes.Get(nodeId));
        const Vector sinkPos = GetPosition(m_sinkNode);
        return CalculateDistance(nodePos, sinkPos);
    }

  private:
    LeachConfig m_config;
    NodeContainer m_sensorNodes;
    NodeContainer m_allNodes;
    Ptr<Node> m_sinkNode;
    NetDeviceContainer m_sensorDevices;
    NetDeviceContainer m_allDevices;
    Ipv4InterfaceContainer m_interfaces;
    std::vector<Ptr<energy::BasicEnergySource>> m_energySources;
    std::vector<LeachNodeState> m_states;
    std::map<uint32_t, std::vector<uint32_t>> m_clusters;
    std::map<uint32_t, uint32_t> m_memberToCh;
    std::vector<Ptr<Socket>> m_txSockets;
    Ptr<UniformRandomVariable> m_uniformRv;
    std::vector<RoundStats> m_roundStats;
    uint64_t m_nextSequence = 1;
    uint64_t m_totalActualPacketsSent = 0;
    uint64_t m_totalActualPacketsReceivedAtSink = 0;
    uint64_t m_totalLogicalReportsAtSink = 0;
    uint64_t m_totalPacketsGenerated = 0;
    double m_cumulativeEnergyConsumed = 0.0;
    int32_t m_firstNodeDeathRound = -1;
    int32_t m_halfNodesDeadRound = -1;
    int32_t m_lastNodeDeathRound = -1;
    uint32_t m_completedRounds = 0;
    AnimationInterface* m_anim = nullptr;
    Ptr<FlowMonitor> m_flowMonitor;
    std::unique_ptr<FlowMonitorHelper> m_flowMonitorHelper;
    std::string m_resultsDir;
    std::ofstream m_metricsFile;
    std::ofstream m_clusterHistoryFile;
    std::ofstream m_nodeEnergyFile;
    std::ofstream m_packetsFile;
};

void
SensorReceiverApp::StartApplication()
{
    if (m_socket == nullptr)
    {
        m_socket = Socket::CreateSocket(GetNode(), UdpSocketFactory::GetTypeId());
        m_socket->Bind(InetSocketAddress(Ipv4Address::GetAny(), m_port));
    }
    m_socket->SetRecvCallback(MakeCallback(&SensorReceiverApp::HandleRead, this));
}

void
SensorReceiverApp::StopApplication()
{
    if (m_socket != nullptr)
    {
        m_socket->SetRecvCallback(MakeNullCallback<void, Ptr<Socket>>());
        m_socket->Close();
        m_socket = nullptr;
    }
}

void
SensorReceiverApp::HandleRead(Ptr<Socket> socket)
{
    Address from;
    while (Ptr<Packet> packet = socket->RecvFrom(from))
    {
        if (m_controller != nullptr)
        {
            m_controller->HandleSensorPacket(m_nodeId, packet, from);
        }
    }
}

void
SinkReceiverApp::StartApplication()
{
    if (m_socket == nullptr)
    {
        m_socket = Socket::CreateSocket(GetNode(), UdpSocketFactory::GetTypeId());
        m_socket->Bind(InetSocketAddress(Ipv4Address::GetAny(), m_port));
    }
    m_socket->SetRecvCallback(MakeCallback(&SinkReceiverApp::HandleRead, this));
}

void
SinkReceiverApp::StopApplication()
{
    if (m_socket != nullptr)
    {
        m_socket->SetRecvCallback(MakeNullCallback<void, Ptr<Socket>>());
        m_socket->Close();
        m_socket = nullptr;
    }
}

void
SinkReceiverApp::HandleRead(Ptr<Socket> socket)
{
    Address from;
    while (Ptr<Packet> packet = socket->RecvFrom(from))
    {
        if (m_controller != nullptr)
        {
            m_controller->HandleSinkPacket(packet, from);
        }
    }
}

} // namespace

int
main(int argc, char* argv[])
{
    Time::SetResolution(Time::NS);

    LeachConfig config;

    CommandLine cmd(__FILE__);
    cmd.AddValue("nNodes", "Number of sensor nodes.", config.nNodes);
    cmd.AddValue("areaX", "Deployment area width (m).", config.areaX);
    cmd.AddValue("areaY", "Deployment area height (m).", config.areaY);
    cmd.AddValue("sinkX", "Sink X coordinate (m).", config.sinkX);
    cmd.AddValue("sinkY", "Sink Y coordinate (m).", config.sinkY);
    cmd.AddValue("initialEnergy", "Initial energy per sensor node (J).", config.initialEnergy);
    cmd.AddValue("chProbability", "LEACH cluster-head probability p.", config.chProbability);
    cmd.AddValue("packetSize", "Application payload size in bytes.", config.packetSize);
    cmd.AddValue("rounds", "Number of LEACH rounds.", config.rounds);
    cmd.AddValue("roundDuration", "Duration of one round in seconds.", config.roundDuration);
    cmd.AddValue("setupDuration", "Setup phase duration in seconds.", config.setupDuration);
    cmd.AddValue("dataInterval",
                 "Preferred TDMA slot duration in seconds. Use 0 for auto.",
                 config.dataInterval);
    cmd.AddValue("slotsPerRound",
                 "Preferred TDMA slots per cluster round when dataInterval=0.",
                 config.slotsPerRound);
    cmd.AddValue("txRange", "RangePropagationLossModel max range (m).", config.txRange);
    cmd.AddValue("enableFlowMonitor",
                 "Enable FlowMonitor XML output (0/1).",
                 config.enableFlowMonitor);
    cmd.AddValue("enableNetAnim", "Enable NetAnim XML output (0/1).", config.enableNetAnim);
    cmd.AddValue("run", "NS-3 RNG run number.", config.run);
    cmd.AddValue("seed", "NS-3 RNG seed.", config.seed);
    cmd.AddValue("outputTag", "Optional tag inserted into the results folder name.", config.outputTag);
    cmd.Parse(argc, argv);

    LeachController controller(config);
    controller.Initialize();

    Simulator::Stop(Seconds(config.rounds * config.roundDuration + 1.0));
    Simulator::Run();
    controller.Finalize();
    Simulator::Destroy();

    return 0;
}
