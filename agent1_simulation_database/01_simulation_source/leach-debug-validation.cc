/* =======================================================================
 *  leach-debug-validation.cc
 *
 *  Test-only NS-3 LEACH validation harness for self-healing WSN research.
 *  Folder: <VM_WORKSPACE_PATH>/test-ns3/
 *
 *  What this test adds:
 *    1) Clustering correctness logs + assertions
 *    2) WifiRadioEnergyModel validation (per-round breakdown)
 *    3) Packet flow validation + sink packet assertions
 *    4) NetAnim role colors + packet metadata enabled
 *    5) Failure simulation, Friis propagation, FlowMonitor, CSV metrics
 *
 *  Build & run:
 *    cp <VM_WORKSPACE_PATH>/test-ns3/leach-debug-validation.cc scratch/
 *    ./ns3 build scratch/leach-debug-validation
 *    ./ns3 run "scratch/leach-debug-validation --nodes=20 --failCount=2"
 * ======================================================================= */

#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/internet-module.h"
#include "ns3/applications-module.h"
#include "ns3/wifi-module.h"
#include "ns3/mobility-module.h"
#include "ns3/energy-module.h"
#include "ns3/netanim-module.h"
#include "ns3/flow-monitor-module.h"

#include <vector>
#include <map>
#include <set>
#include <cmath>
#include <algorithm>
#include <iomanip>
#include <fstream>
#include <filesystem>
#include <sstream>
#include <chrono>
#include <ctime>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE ("LeachDebugValidation");

/* ------------------------------- Defaults ------------------------------ */
static uint32_t G_NODES            = 20;
static double   G_AREA_W           = 50.0;
static double   G_AREA_H           = 50.0;
static double   G_SINK_X           = 25.0;
static double   G_SINK_Y           = 25.0;
static double   G_CH_PROB          = 0.1;
static uint32_t G_ROUNDS           = 5;
static double   G_ROUND_SEC        = 30.0;
static double   G_SETUP_SEC        = 5.0;
static double   G_DATA_INT_SEC     = 10.0;       // => 2 slots
static double   G_INITIAL_ENERGY_J = 2.0;
static double   G_COMM_RANGE_M     = 60.0;

static uint16_t SINK_PORT = 9;
static uint16_t CH_PORT   = 10;
static uint16_t ACK_PORT  = 11;

/* WifiRadioEnergyModel currents */
static double G_TX_A    = 0.0174;
static double G_RX_A    = 0.0197;
static double G_IDLE_A  = 0.000426;
static double G_SLEEP_A = 0.0000142;
static double G_VOLT    = 3.0;                  // BasicEnergySource default

/* Failure simulation */
static uint32_t G_FAIL_COUNT = 2;               // kill 1-2 nodes mid-run
static uint32_t G_FAIL_ROUND = 2;               // 0-based
static double   G_FAIL_OFFSET_SEC = 10.0;       // inside round
static bool     G_STRICT_SINK_ASSERT = false;   // enforce exact sink packets

static const std::string RESULTS_BASE = "<VM_HOME_PATH>/ns-allinone-3.42/ns-3.42/results";
static std::string RESULTS_DIR;

static std::string
MakeResultsDir ()
{
    auto now = std::chrono::system_clock::now ();
    auto tt = std::chrono::system_clock::to_time_t (now);
    std::tm tm{};
    localtime_r (&tt, &tm);
    char buf[64];
    std::strftime (buf, sizeof (buf), "%Y-%m-%d_%H-%M-%S", &tm);
    return RESULTS_BASE + "/test_ns3_leach_" + std::string (buf);
}

/* ------------------------------- Globals ------------------------------- */
static NodeContainer g_sensorNodes;
static Ptr<Node> g_sinkNode;
static NodeContainer g_allNodes;
static Ipv4InterfaceContainer g_ifaces;          // [0..N-1] sensors, [N] sink
static std::vector<Ptr<energy::EnergySource>> g_energy;
static std::vector<double> g_prevEnergy;

static uint32_t g_currRound = 0;
static uint32_t g_sinkPktRx = 0;
static uint32_t g_sinkAtRoundStart = 0;

static std::vector<bool> g_failed;
static std::vector<double> g_failTime;           // -1 if alive

static AnimationInterface* g_anim = nullptr;

/* per-round temporary accounting */
struct NodeRoundAcct
{
    uint32_t txPkts = 0;
    uint32_t rxPkts = 0;
    double txTime = 0.0;
    double rxTime = 0.0;
};
static std::vector<NodeRoundAcct> g_roundAcct;

struct RoundRecord
{
    uint32_t round = 0;
    std::vector<uint32_t> chs;
    std::map<uint32_t, std::vector<uint32_t>> clusters;
    uint32_t expectedSinkPkts = 0;
    uint32_t sinkPkts = 0;
    double pdr = 0.0;
    double energyVariance = 0.0;
    double avgHops = 1.0;
};
static std::vector<RoundRecord> g_roundRecords;

struct SinkPktRecord
{
    double t;
    uint32_t round;
    uint32_t src;
    uint32_t seq;
};
static std::vector<SinkPktRecord> g_sinkLog;

struct EnergySnapshot
{
    uint32_t round;
    uint32_t node;
    double residual;
    double pct;
};
static std::vector<EnergySnapshot> g_energySnap;

/* ------------------------------- Helpers ------------------------------- */
static inline uint32_t
SinkNodeIndex ()
{
    return G_NODES;
}

static Vector
GetPos (Ptr<Node> n)
{
    return n->GetObject<MobilityModel> ()->GetPosition ();
}

static double
NodeDist (uint32_t a, uint32_t b)
{
    Ptr<Node> na = (a < G_NODES) ? g_sensorNodes.Get (a) : g_sinkNode;
    Ptr<Node> nb = (b < G_NODES) ? g_sensorNodes.Get (b) : g_sinkNode;
    Vector pa = GetPos (na);
    Vector pb = GetPos (nb);
    return std::sqrt ((pa.x - pb.x) * (pa.x - pb.x) + (pa.y - pb.y) * (pa.y - pb.y));
}

static uint32_t
IpToNodeId (Ipv4Address addr)
{
    for (uint32_t i = 0; i < g_ifaces.GetN (); ++i)
    {
        if (g_ifaces.GetAddress (i) == addr)
            return i;
    }
    return UINT32_MAX;
}

static double
EstimateRssiDbm (double distM)
{
    /* Friis received power (rough estimate for debug logging) */
    const double txDbm = 0.0;
    const double freq = 2.4e9;
    const double c = 299792458.0;
    const double lambda = c / freq;
    double d = std::max (distM, 0.1);
    double prDbm = txDbm + 20.0 * std::log10 (lambda / (4.0 * M_PI * d));
    return prDbm;
}

static bool
RoundHasFailure (uint32_t round)
{
    double rs = round * G_ROUND_SEC;
    double re = (round + 1) * G_ROUND_SEC;
    for (uint32_t i = 0; i < G_NODES; ++i)
    {
        if (g_failTime[i] >= rs && g_failTime[i] < re)
            return true;
    }
    return false;
}

static void
FailNode (uint32_t nodeId)
{
    if (nodeId >= G_NODES || g_failed[nodeId])
        return;

    g_failed[nodeId] = true;
    g_failTime[nodeId] = Simulator::Now ().GetSeconds ();

    if (g_anim)
        g_anim->UpdateNodeColor (g_sensorNodes.Get (nodeId), 128, 128, 128); // gray

    NS_LOG_WARN ("[FAILURE] Node " << nodeId << " failed at t="
                 << Simulator::Now ().GetSeconds () << " s");
}

/* -------------------------- Forward declarations ----------------------- */
static void InstallMemberApp (Ptr<Node> node, Ipv4Address chAddr);
static void InstallCHApp    (Ptr<Node> chNode, Ipv4Address sinkAddr);
static void SinkSetupBroadcast (uint32_t round);
static void EndOfRound (uint32_t round);

/* ----------------------------- Sink app -------------------------------- */
class SinkApp : public Application
{
public:
    static TypeId GetTypeId ()
    {
        static TypeId tid = TypeId ("ns3::SinkAppDebug")
            .SetParent<Application> ()
            .AddConstructor<SinkApp> ();
        return tid;
    }

private:
    void StartApplication () override
    {
        if (!m_sock)
        {
            m_sock = Socket::CreateSocket (GetNode (), TypeId::LookupByName ("ns3::UdpSocketFactory"));
            m_sock->Bind (InetSocketAddress (Ipv4Address::GetAny (), SINK_PORT));
        }
        m_sock->SetRecvCallback (MakeCallback (&SinkApp::HandleRead, this));
    }

    void StopApplication () override
    {
        if (m_sock)
        {
            m_sock->Close ();
            m_sock->SetRecvCallback (MakeNullCallback<void, Ptr<Socket>> ());
        }
    }

    void HandleRead (Ptr<Socket> s)
    {
        Ptr<Packet> p;
        Address from;
        while ((p = s->RecvFrom (from)))
        {
            ++g_sinkPktRx;
            Ipv4Address src = InetSocketAddress::ConvertFrom (from).GetIpv4 ();
            uint32_t srcId = IpToNodeId (src);

            g_sinkLog.push_back ({Simulator::Now ().GetSeconds (), g_currRound, srcId, g_sinkPktRx});

            NS_LOG_INFO ("[FLOW] CH " << srcId
                         << " -> sink: agg_pkt#" << g_sinkPktRx
                         << ", size=" << p->GetSize ()
                         << "B, path=[" << srcId << ",sink]");

            /* ACK back to CH so NetAnim shows reverse sink->CH direction. */
            if (srcId < G_NODES)
            {
                Ptr<Socket> ack = Socket::CreateSocket (GetNode (),
                                    TypeId::LookupByName ("ns3::UdpSocketFactory"));
                ack->Connect (InetSocketAddress (src, ACK_PORT));
                Ptr<Packet> ackPkt = Create<Packet> (24);
                ack->Send (ackPkt);
                ack->Close ();

                NS_LOG_INFO ("[FLOW] sink -> CH " << srcId
                             << ": ack_pkt, size=24B, path=[sink," << srcId << "]");
            }
        }
    }

    Ptr<Socket> m_sock;
};
NS_OBJECT_ENSURE_REGISTERED (SinkApp);

class ChReceiverApp : public Application
{
public:
    static TypeId GetTypeId ()
    {
        static TypeId tid = TypeId ("ns3::ChReceiverAppDebug")
            .SetParent<Application> ()
            .AddConstructor<ChReceiverApp> ();
        return tid;
    }

private:
    void StartApplication () override
    {
        if (!m_sock)
        {
            m_sock = Socket::CreateSocket (GetNode (), TypeId::LookupByName ("ns3::UdpSocketFactory"));
            m_sock->Bind (InetSocketAddress (Ipv4Address::GetAny (), CH_PORT));
        }
        m_sock->SetRecvCallback (MakeCallback (&ChReceiverApp::HandleRead, this));
    }

    void StopApplication () override
    {
        if (m_sock)
        {
            m_sock->Close ();
            m_sock->SetRecvCallback (MakeNullCallback<void, Ptr<Socket>> ());
        }
    }

    void HandleRead (Ptr<Socket> s)
    {
        Ptr<Packet> p;
        Address from;
        while ((p = s->RecvFrom (from)))
        {
            uint32_t me = GetNode ()->GetId (); // equals sensor id here
            Ipv4Address src = InetSocketAddress::ConvertFrom (from).GetIpv4 ();
            uint32_t srcId = IpToNodeId (src);

            if (me < G_NODES)
            {
                g_roundAcct[me].rxPkts++;
                g_roundAcct[me].rxTime += (p->GetSize () * 8.0 / 1e6); // 1 Mbps data mode
            }

            NS_LOG_INFO ("[FLOW] Node " << srcId << " -> CH " << me
                         << ": pkt, size=" << p->GetSize () << "B");
        }
    }

    Ptr<Socket> m_sock;
};
NS_OBJECT_ENSURE_REGISTERED (ChReceiverApp);

class AckReceiverApp : public Application
{
public:
    static TypeId GetTypeId ()
    {
        static TypeId tid = TypeId ("ns3::AckReceiverAppDebug")
            .SetParent<Application> ()
            .AddConstructor<AckReceiverApp> ();
        return tid;
    }

private:
    void StartApplication () override
    {
        if (!m_sock)
        {
            m_sock = Socket::CreateSocket (GetNode (), TypeId::LookupByName ("ns3::UdpSocketFactory"));
            m_sock->Bind (InetSocketAddress (Ipv4Address::GetAny (), ACK_PORT));
        }
        m_sock->SetRecvCallback (MakeCallback (&AckReceiverApp::HandleRead, this));
    }

    void StopApplication () override
    {
        if (m_sock)
        {
            m_sock->Close ();
            m_sock->SetRecvCallback (MakeNullCallback<void, Ptr<Socket>> ());
        }
    }

    void HandleRead (Ptr<Socket> s)
    {
        Ptr<Packet> p;
        Address from;
        while ((p = s->RecvFrom (from)))
        {
            uint32_t me = GetNode ()->GetId ();
            Ipv4Address src = InetSocketAddress::ConvertFrom (from).GetIpv4 ();
            uint32_t srcId = IpToNodeId (src);
            NS_LOG_INFO ("[FLOW] sink-ack: Node " << me << " <= " << srcId
                         << ", size=" << p->GetSize () << "B");
        }
    }

    Ptr<Socket> m_sock;
};
NS_OBJECT_ENSURE_REGISTERED (AckReceiverApp);

/* ----------------------------- LEACH core ------------------------------ */
class LeachProtocol
{
public:
    LeachProtocol () : m_roundEpoch (0), m_epochLen (static_cast<uint32_t> (std::round (1.0 / G_CH_PROB))) {}

    void Init ()
    {
        m_rng = CreateObject<UniformRandomVariable> ();
        m_rng->SetAttribute ("Min", DoubleValue (0.0));
        m_rng->SetAttribute ("Max", DoubleValue (1.0));
    }

    void StartRound (uint32_t round)
    {
        g_currRound = round;
        g_sinkAtRoundStart = g_sinkPktRx;
        std::fill (g_roundAcct.begin (), g_roundAcct.end (), NodeRoundAcct{});

        if (m_roundEpoch >= m_epochLen)
        {
            m_recentCH.clear ();
            m_roundEpoch = 0;
        }

        SelectCHs (round);
        FormClusters ();
        ColorizeRoundRoles ();

        m_expectedSinkRound = static_cast<uint32_t> (m_chs.size ());

        RoundRecord rr;
        rr.round = round;
        rr.chs.assign (m_chs.begin (), m_chs.end ());
        for (auto &kv : m_memberToCH)
            rr.clusters[kv.second].push_back (kv.first);
        rr.expectedSinkPkts = m_expectedSinkRound;
        g_roundRecords.push_back (rr);

        Simulator::Schedule (Seconds (0.0), &LeachProtocol::ScheduleDataPhase, this);

        m_roundEpoch++;
    }

private:
    void SelectCHs (uint32_t round)
    {
        m_chs.clear ();
        m_memberToCH.clear ();

        uint32_t rMod = m_roundEpoch % m_epochLen;
        double denom = 1.0 - G_CH_PROB * static_cast<double> (rMod);
        if (denom <= 0.0) denom = 1e-6;
        double t = G_CH_PROB / denom;

        std::vector<uint32_t> elected;
        std::vector<double> electedE;

        for (uint32_t i = 0; i < G_NODES; ++i)
        {
            if (g_failed[i])
                continue;
            if (m_recentCH.count (i))
                continue;
            if (m_rng->GetValue () < t)
            {
                m_chs.insert (i);
                m_recentCH.insert (i);
                elected.push_back (i);
                electedE.push_back (g_energy[i]->GetRemainingEnergy ());
            }
        }

        if (m_chs.empty ())
        {
            uint32_t bestNode = UINT32_MAX;
            double bestE = -1.0;
            for (uint32_t i = 0; i < G_NODES; ++i)
            {
                if (g_failed[i]) continue;
                if (m_recentCH.count (i)) continue;
                double e = g_energy[i]->GetRemainingEnergy ();
                if (e > bestE) { bestE = e; bestNode = i; }
            }
            if (bestNode == UINT32_MAX)
            {
                m_recentCH.clear ();
                for (uint32_t i = 0; i < G_NODES; ++i)
                {
                    if (g_failed[i]) continue;
                    double e = g_energy[i]->GetRemainingEnergy ();
                    if (e > bestE) { bestE = e; bestNode = i; }
                }
            }
            if (bestNode != UINT32_MAX)
            {
                m_chs.insert (bestNode);
                m_recentCH.insert (bestNode);
                elected.push_back (bestNode);
                electedE.push_back (g_energy[bestNode]->GetRemainingEnergy ());
            }
        }

        std::ostringstream ossIds;
        std::ostringstream ossE;
        for (size_t i = 0; i < elected.size (); ++i)
        {
            if (i) { ossIds << ","; ossE << ","; }
            ossIds << elected[i];
            ossE << std::fixed << std::setprecision (4) << electedE[i];
        }

        NS_LOG_INFO ("[CLUSTER] round " << round << ": CHs elected = [" << ossIds.str ()
                     << "], energy=[" << ossE.str () << "]");
        NS_ASSERT_MSG (!m_chs.empty (), "No CH elected. Check CH selection path.");
    }

    void FormClusters ()
    {
        for (uint32_t n = 0; n < G_NODES; ++n)
        {
            if (g_failed[n] || m_chs.count (n))
                continue;

            double bestRssi = -1e9;
            double bestDist = 1e12;
            uint32_t bestCh = UINT32_MAX;

            for (auto ch : m_chs)
            {
                if (g_failed[ch]) continue;
                double d = NodeDist (n, ch);
                if (d > G_COMM_RANGE_M)
                    continue;
                double rssi = EstimateRssiDbm (d);
                if (rssi > bestRssi)
                {
                    bestRssi = rssi;
                    bestDist = d;
                    bestCh = ch;
                }
            }

            if (bestCh == UINT32_MAX)
            {
                /* fallback: nearest CH if all outside range */
                for (auto ch : m_chs)
                {
                    if (g_failed[ch]) continue;
                    double d = NodeDist (n, ch);
                    if (d < bestDist)
                    {
                        bestDist = d;
                        bestCh = ch;
                        bestRssi = EstimateRssiDbm (d);
                    }
                }
                NS_LOG_WARN ("[CLUSTER] Node " << n << " has no CH within range; nearest CH fallback.");
            }

            NS_ASSERT_MSG (bestCh != UINT32_MAX, "Member cannot find any CH.");
            NS_ASSERT_MSG (bestDist <= G_COMM_RANGE_M + 15.0,
                           "Member joined CH too far away for expected range model.");

            m_memberToCH[n] = bestCh;
            NS_LOG_INFO ("[CLUSTER] Node " << n << " joins CH " << bestCh
                         << " (RSSI=" << std::fixed << std::setprecision (2) << bestRssi
                         << " dBm, distance=" << std::setprecision (2) << bestDist << "m)");
        }
    }

    void ScheduleDataPhase ()
    {
        // Build clusterMap: nodeID -> CH ID
        std::map<uint32_t, uint32_t> clusterMap;
        for (auto ch : m_chs)
            clusterMap[ch] = ch;
        for (auto &kv : m_memberToCH)
            clusterMap[kv.first] = kv.second;

        // === STEADY-STATE PHASE: Unicast data ===
        // Key design: Install() triggers DoInitialize() immediately, which schedules
        // StartApplication at (m_startTime - Now()).  To avoid the stale m_startTime=0
        // bug we defer the Install() call itself to the desired start offset so that
        // the app fires right when it is installed.

        // Setup phase visual cue: sink broadcasts setup info (offset +0.2 s)
        Simulator::Schedule (Seconds (0.2), &SinkSetupBroadcast, g_currRound);

        // MEMBER -> CH  (staggered: slot 0 at +5 s, slot 1 at +15 s)
        for (uint32_t i = 0; i < G_NODES; ++i)
        {
            if (g_failed[i]) continue;
            if (clusterMap.count (i) == 0) continue;
            if (clusterMap[i] == i) continue;  // skip CHs

            Ptr<Node>    node   = g_allNodes.Get (i);
            Ipv4Address  chAddr = g_ifaces.GetAddress (clusterMap[i], 0);
            double       delay  = 5.0 + (i % 2) * 10.0;  // 5 s or 15 s

            // Schedule the Install() call at the right relative time
            Simulator::Schedule (Seconds (delay), &InstallMemberApp, node, chAddr);
        }

        // CH -> SINK  (start at +22 s — after slot-1 member burst at +15 s clears,
        //              stagger CHs by 0.2 s each, stop 8 s later = round end)
        Ipv4Address sinkAddr = g_ifaces.GetAddress (SinkNodeIndex (), 0);
        uint32_t ci = 0;
        for (auto &ch : m_chs)
        {
            if (g_failed[ch]) { ++ci; continue; }

            Ptr<Node> chNode = g_allNodes.Get (ch);
            double    delay  = 22.0 + ci * 0.2;

            Simulator::Schedule (Seconds (delay), &InstallCHApp, chNode, sinkAddr);
            ++ci;
        }
    }

    void ColorizeRoundRoles ()
    {
        if (!g_anim) return;

        for (uint32_t i = 0; i < G_NODES; ++i)
        {
            if (g_failed[i])
            {
                g_anim->UpdateNodeColor (g_sensorNodes.Get (i), 128, 128, 128); // gray
            }
            else if (m_chs.count (i))
            {
                g_anim->UpdateNodeColor (g_sensorNodes.Get (i), 255, 165, 0);   // orange CH
            }
            else
            {
                g_anim->UpdateNodeColor (g_sensorNodes.Get (i), 0, 200, 0);     // green member
            }
        }
        g_anim->UpdateNodeColor (g_sinkNode, 255, 0, 0);                         // red sink
    }

private:
    std::set<uint32_t> m_chs;
    std::map<uint32_t, uint32_t> m_memberToCH;
    std::set<uint32_t> m_recentCH;
    uint32_t m_roundEpoch;
    uint32_t m_epochLen;
    Ptr<UniformRandomVariable> m_rng;
    uint32_t m_expectedSinkRound = 0;
};

static LeachProtocol g_leach;

/* -------- Deferred app installers (called via Simulator::Schedule) ----- */
// These are invoked at the desired start time so that DoInitialize() fires
// the UdpEchoClient immediately — avoiding the stale m_startTime=0 bug that
// occurs when Install() is called before Start() in a mid-simulation callback.

static void
InstallMemberApp (Ptr<Node> node, Ipv4Address chAddr)
{
    // Now() == desired start time; DoInitialize will schedule Send at delay=0
    UdpEchoClientHelper client (chAddr, CH_PORT);
    client.SetAttribute ("MaxPackets", UintegerValue (1));
    client.SetAttribute ("Interval",   TimeValue (Seconds (10.0)));
    client.SetAttribute ("PacketSize", UintegerValue (64));
    ApplicationContainer app = client.Install (node);
    // Stop 25 s after install (well within the 30 s round window)
    app.Stop (Simulator::Now () + Seconds (25.0));
    NS_LOG_INFO ("[FLOW] member-app installed on node "
                 << node->GetId () << " -> CH " << chAddr
                 << " at t=" << Simulator::Now ().GetSeconds () << "s");
}

static void
InstallCHApp (Ptr<Node> chNode, Ipv4Address sinkAddr)
{
    // Now() == desired start time
    UdpEchoClientHelper chToSink (sinkAddr, SINK_PORT);
    chToSink.SetAttribute ("MaxPackets", UintegerValue (1));
    chToSink.SetAttribute ("Interval",   TimeValue (Seconds (10.0)));
    chToSink.SetAttribute ("PacketSize", UintegerValue (128));
    ApplicationContainer app = chToSink.Install (chNode);
    app.Stop (Simulator::Now () + Seconds (8.0));
    NS_LOG_INFO ("[FLOW] CH-app installed on node "
                 << chNode->GetId () << " -> sink " << sinkAddr
                 << " at t=" << Simulator::Now ().GetSeconds () << "s");
}

static void
SinkSetupBroadcast (uint32_t round)
{
    Ptr<Node> sink = g_sinkNode;
    for (uint32_t i = 0; i < G_NODES; ++i)
    {
        if (g_failed[i])
            continue;

        Ipv4Address dst = g_ifaces.GetAddress (i);
        Ptr<Socket> sock = Socket::CreateSocket (sink,
                           TypeId::LookupByName ("ns3::UdpSocketFactory"));
        sock->Connect (InetSocketAddress (dst, CH_PORT));
        Ptr<Packet> p = Create<Packet> (32);
        sock->Send (p);
        sock->Close ();
    }
    NS_LOG_INFO ("[SETUP] Round " << round << " sink broadcast/unicast setup msgs to members");
}

/* ------------------------------- Round end ----------------------------- */
static void
EndOfRound (uint32_t round)
{
    NS_ASSERT_MSG (round < g_roundRecords.size (), "Round record missing at EndOfRound");

    uint32_t sinkThisRound = g_sinkPktRx - g_sinkAtRoundStart;
    g_roundRecords[round].sinkPkts = sinkThisRound;

    uint32_t expected = g_roundRecords[round].expectedSinkPkts;
    NS_ASSERT_MSG (sinkThisRound <= expected,
                   "Sink packets exceeded expected CH->sink packet count.");

    if (!RoundHasFailure (round) && G_STRICT_SINK_ASSERT)
    {
        NS_ASSERT_MSG (sinkThisRound == expected,
                       "Strict mode: sink packets mismatch in non-failure round.");
    }
    else if (!RoundHasFailure (round) && sinkThisRound != expected)
    {
        NS_LOG_WARN ("[VALIDATION] round " << round
                     << " sinkRx=" << sinkThisRound
                     << " expected=" << expected
                     << " (likely contention/collision/loss)");
    }

    g_roundRecords[round].pdr = (expected == 0) ? 1.0 : static_cast<double> (sinkThisRound) / expected;

    double sumE = 0.0;
    for (uint32_t i = 0; i < G_NODES; ++i)
        sumE += g_energy[i]->GetRemainingEnergy ();
    double meanE = sumE / G_NODES;
    double var = 0.0;
    for (uint32_t i = 0; i < G_NODES; ++i)
    {
        double d = g_energy[i]->GetRemainingEnergy () - meanE;
        var += d * d;
    }
    var /= G_NODES;
    g_roundRecords[round].energyVariance = var;

    std::set<uint32_t> chSet (g_roundRecords[round].chs.begin (), g_roundRecords[round].chs.end ());

    for (uint32_t i = 0; i < G_NODES; ++i)
    {
        double rs = round * G_ROUND_SEC;
        double re = (round + 1) * G_ROUND_SEC;
        double sleepT = 0.0;
        if (g_failTime[i] >= 0.0)
        {
            double s = std::max (g_failTime[i], rs);
            if (s < re)
                sleepT = re - s;
        }

        double txJ = G_TX_A * G_VOLT * g_roundAcct[i].txTime;
        double rxJ = G_RX_A * G_VOLT * g_roundAcct[i].rxTime;
        double idleT = std::max (0.0, G_ROUND_SEC - g_roundAcct[i].txTime - g_roundAcct[i].rxTime - sleepT);
        double idleJ = G_IDLE_A * G_VOLT * idleT;
        double sleepJ = G_SLEEP_A * G_VOLT * sleepT;

        double rem = g_energy[i]->GetRemainingEnergy ();
        double actualDrain = std::max (0.0, g_prevEnergy[i] - rem);
        g_prevEnergy[i] = rem;

        g_energySnap.push_back ({round, i, rem, 100.0 * rem / G_INITIAL_ENERGY_J});

        bool isMember = (!chSet.count (i) && !g_failed[i]);
        if (isMember)
        {
            NS_ASSERT_MSG (actualDrain <= 0.1 + 1e-6,
                           "Member drained >0.1J/round. Check MAC/idle behavior.");
        }

        NS_LOG_INFO ("[ENERGY] Round " << round << ": Node " << i
                     << " tx=" << std::fixed << std::setprecision (6) << txJ
                     << " J, rx=" << rxJ
                     << " J, idle=" << idleJ
                     << " J, sleep=" << sleepJ
                     << " J, actualDrain=" << actualDrain << " J");
    }

    std::cout << "[ROUND " << round << "]"
              << " CHs=" << g_roundRecords[round].chs.size ()
              << " expectedSink=" << expected
              << " sinkRx=" << sinkThisRound
              << " PDR=" << std::fixed << std::setprecision (3) << g_roundRecords[round].pdr
              << " EnergyVar=" << std::setprecision (8) << g_roundRecords[round].energyVariance
              << (RoundHasFailure (round) ? " [FAILURE-ROUND]" : "")
              << "\n";
}

/* -------------------------------- main -------------------------------- */
int
main (int argc, char** argv)
{
    CommandLine cmd (__FILE__);
    cmd.AddValue ("nodes", "Number of sensor nodes (20..100)", G_NODES);
    cmd.AddValue ("rounds", "Number of rounds", G_ROUNDS);
    cmd.AddValue ("failCount", "Number of nodes to fail mid-run (0..2)", G_FAIL_COUNT);
    cmd.AddValue ("failRound", "0-based round for failures", G_FAIL_ROUND);
    cmd.AddValue ("strictSinkAssert", "If true, enforce exact sink packets in non-failure rounds", G_STRICT_SINK_ASSERT);
    cmd.Parse (argc, argv);

    NS_ASSERT_MSG (G_NODES >= 20 && G_NODES <= 100, "nodes must be in [20,100]");
    NS_ASSERT_MSG (G_FAIL_COUNT <= 2, "failCount max supported is 2");

    /* Debug logging requested */
    LogComponentEnable ("LeachDebugValidation", LOG_LEVEL_DEBUG);
    LogComponentEnable ("WifiRadioEnergyModel", LOG_LEVEL_DEBUG);
    LogComponentEnable ("AdhocWifiMac", LOG_LEVEL_DEBUG);
    LogComponentEnable ("Ipv4StaticRouting", LOG_LEVEL_DEBUG);

    RESULTS_DIR = MakeResultsDir ();
    std::filesystem::create_directories (RESULTS_DIR);

    g_sensorNodes.Create (G_NODES);
    NodeContainer sinkC;
    sinkC.Create (1);
    g_sinkNode = sinkC.Get (0);

    g_allNodes = NodeContainer ();
    g_allNodes.Add (g_sensorNodes);
    g_allNodes.Add (g_sinkNode);

    /* fixed positions (no mobility) */
    Ptr<ListPositionAllocator> pos = CreateObject<ListPositionAllocator> ();
    Ptr<UniformRandomVariable> rx = CreateObject<UniformRandomVariable> ();
    Ptr<UniformRandomVariable> ry = CreateObject<UniformRandomVariable> ();
    rx->SetAttribute ("Min", DoubleValue (2.0));
    rx->SetAttribute ("Max", DoubleValue (G_AREA_W - 2.0));
    ry->SetAttribute ("Min", DoubleValue (2.0));
    ry->SetAttribute ("Max", DoubleValue (G_AREA_H - 2.0));

    for (uint32_t i = 0; i < G_NODES; ++i)
        pos->Add (Vector (rx->GetValue (), ry->GetValue (), 0.0));
    pos->Add (Vector (G_SINK_X, G_SINK_Y, 0.0));

    MobilityHelper mob;
    mob.SetPositionAllocator (pos);
    mob.SetMobilityModel ("ns3::ConstantPositionMobilityModel");
    mob.Install (g_allNodes);

    /* WiFi ad-hoc + Friis propagation */
    WifiHelper wifi;
    wifi.SetStandard (WIFI_STANDARD_80211b);
    wifi.SetRemoteStationManager ("ns3::AarfWifiManager");

    YansWifiPhyHelper phy;
    YansWifiChannelHelper ch;
    ch.SetPropagationDelay ("ns3::ConstantSpeedPropagationDelayModel");
    ch.AddPropagationLoss ("ns3::FriisPropagationLossModel");
    phy.SetChannel (ch.Create ());
    phy.Set ("TxPowerStart", DoubleValue (0.0));
    phy.Set ("TxPowerEnd", DoubleValue (0.0));

    WifiMacHelper mac;
    mac.SetType ("ns3::AdhocWifiMac");

    NetDeviceContainer devs = wifi.Install (phy, mac, g_allNodes);

    InternetStackHelper internet;
    internet.Install (g_allNodes);

    Ipv4AddressHelper ipv4;
    ipv4.SetBase ("10.9.0.0", "255.255.255.0");
    g_ifaces = ipv4.Assign (devs);
    Ipv4GlobalRoutingHelper::PopulateRoutingTables ();

    /* Energy: sensors only, sink treated as infinite */
    BasicEnergySourceHelper es;
    es.Set ("BasicEnergySourceInitialEnergyJ", DoubleValue (G_INITIAL_ENERGY_J));
    energy::EnergySourceContainer esc = es.Install (g_sensorNodes);

    g_energy.clear ();
    for (uint32_t i = 0; i < esc.GetN (); ++i)
        g_energy.push_back (esc.Get (i));
    NS_ASSERT_MSG (g_energy.size () == G_NODES, "Energy source not attached to all sensor nodes.");

    WifiRadioEnergyModelHelper em;
    em.Set ("TxCurrentA", DoubleValue (G_TX_A));
    em.Set ("RxCurrentA", DoubleValue (G_RX_A));
    em.Set ("IdleCurrentA", DoubleValue (G_IDLE_A));
    em.Set ("SleepCurrentA", DoubleValue (G_SLEEP_A));
    for (uint32_t i = 0; i < G_NODES; ++i)
        em.Install (devs.Get (i), g_energy[i]);

    NS_LOG_INFO ("[ENERGY] Initial node energies:");
    for (uint32_t i = 0; i < G_NODES; ++i)
    {
        double e = g_energy[i]->GetRemainingEnergy ();
        NS_LOG_INFO ("  node " << i << " = " << std::fixed << std::setprecision (4) << e << " J");
        NS_ASSERT_MSG (std::fabs (e - G_INITIAL_ENERGY_J) < 1e-3, "Initial energy mismatch");
    }
    NS_LOG_INFO ("  sink = infinite (no energy source attached)");

    g_prevEnergy.assign (G_NODES, G_INITIAL_ENERGY_J);
    g_roundAcct.assign (G_NODES, NodeRoundAcct{});
    g_failed.assign (G_NODES, false);
    g_failTime.assign (G_NODES, -1.0);

    /* Apps */
    double simEnd = G_ROUNDS * G_ROUND_SEC + 10.0;

    Ptr<SinkApp> sa = CreateObject<SinkApp> ();
    g_sinkNode->AddApplication (sa);
    sa->SetStartTime (Seconds (0.0));
    sa->SetStopTime (Seconds (simEnd));

    for (uint32_t i = 0; i < G_NODES; ++i)
    {
        Ptr<ChReceiverApp> ra = CreateObject<ChReceiverApp> ();
        g_sensorNodes.Get (i)->AddApplication (ra);
        ra->SetStartTime (Seconds (0.0));
        ra->SetStopTime (Seconds (simEnd));

        Ptr<AckReceiverApp> ack = CreateObject<AckReceiverApp> ();
        g_sensorNodes.Get (i)->AddApplication (ack);
        ack->SetStartTime (Seconds (0.0));
        ack->SetStopTime (Seconds (simEnd));
    }

    FlowMonitorHelper fmHelper;
    Ptr<FlowMonitor> fm = fmHelper.InstallAll ();

    std::string animFile = RESULTS_DIR + "/leach-debug-anim.xml";
    AnimationInterface anim (animFile);
    g_anim = &anim;
    anim.EnablePacketMetadata (true);
    anim.SetMaxPktsPerTraceFile (500000);
    anim.SetMobilityPollInterval (Seconds (1.0));

    for (uint32_t i = 0; i < G_NODES; ++i)
    {
        anim.UpdateNodeDescription (g_sensorNodes.Get (i), "N" + std::to_string (i));
        anim.UpdateNodeColor (g_sensorNodes.Get (i), 0, 200, 0);
    }
    anim.UpdateNodeDescription (g_sinkNode, "SINK");
    anim.UpdateNodeColor (g_sinkNode, 255, 0, 0);

    /* LEACH schedule */
    g_leach.Init ();
    for (uint32_t r = 0; r < G_ROUNDS; ++r)
    {
        Simulator::Schedule (Seconds (r * G_ROUND_SEC), &LeachProtocol::StartRound, &g_leach, r);
        Simulator::Schedule (Seconds ((r + 1) * G_ROUND_SEC - 0.01), &EndOfRound, r);
    }

    /* failure simulation */
    if (G_FAIL_COUNT > 0)
    {
        double t0 = G_FAIL_ROUND * G_ROUND_SEC + G_FAIL_OFFSET_SEC;
        Simulator::Schedule (Seconds (t0), &FailNode, 0u);
        if (G_FAIL_COUNT > 1 && G_NODES > 1)
            Simulator::Schedule (Seconds (t0 + 2.0), &FailNode, 1u);
    }

    Simulator::Stop (Seconds (simEnd));
    Simulator::Run ();

    /* FlowMonitor summary */
    fm->CheckForLostPackets ();
    auto stats = fm->GetFlowStats ();
    uint64_t txPkts = 0, rxPkts = 0;
    double delaySum = 0.0;
    for (const auto &kv : stats)
    {
        txPkts += kv.second.txPackets;
        rxPkts += kv.second.rxPackets;
        delaySum += kv.second.delaySum.GetSeconds ();
    }
    double pdr = (txPkts == 0) ? 0.0 : static_cast<double> (rxPkts) / txPkts;
    double avgLat = (rxPkts == 0) ? 0.0 : delaySum / rxPkts;

    /* FND metric */
    int32_t fndRound = -1;
    for (uint32_t r = 0; r < G_ROUNDS && fndRound < 0; ++r)
    {
        for (const auto &e : g_energySnap)
        {
            if (e.round == r && e.residual <= 1e-6)
            {
                fndRound = static_cast<int32_t> (r);
                break;
            }
        }
    }

    std::cout << "\n==================== TEST SUMMARY ====================\n";
    std::cout << "FlowMonitor txPkts=" << txPkts << " rxPkts=" << rxPkts
              << " PDR=" << std::fixed << std::setprecision (4) << pdr
              << " avgLatency=" << avgLat << " s\n";

    uint32_t steadySlots = static_cast<uint32_t> ((G_ROUND_SEC - G_SETUP_SEC) / G_DATA_INT_SEC);
    if (G_FAIL_COUNT == 0 && G_STRICT_SINK_ASSERT)
    {
        uint32_t totalCh = 0;
        for (const auto &rr : g_roundRecords) totalCh += rr.chs.size ();
        NS_ASSERT_MSG (g_sinkPktRx == totalCh * steadySlots,
                       "Final sink packet assertion failed in no-failure mode.");
    }

    std::cout << "FND round=" << fndRound << " ( -1 means none )\n";

    /* CSV exports */
    {
        std::ofstream ofs (RESULTS_DIR + "/test_metrics.csv");
        ofs << "round,pdr,expectedSinkPkts,sinkPkts,avgHops,energyVariance\n";
        for (const auto &rr : g_roundRecords)
        {
            ofs << rr.round << ","
                << std::fixed << std::setprecision (6) << rr.pdr << ","
                << rr.expectedSinkPkts << ","
                << rr.sinkPkts << ","
                << rr.avgHops << ","
                << rr.energyVariance << "\n";
        }
    }

    {
        std::ofstream ofs (RESULTS_DIR + "/sink_packets.csv");
        ofs << "time,round,srcNode,seq\n";
        for (const auto &r : g_sinkLog)
            ofs << std::fixed << std::setprecision (4) << r.t << "," << r.round << "," << r.src << "," << r.seq << "\n";
    }

    {
        std::ofstream ofs (RESULTS_DIR + "/energy.csv");
        ofs << "round,nodeId,residualEnergy,remainingPct\n";
        for (const auto &e : g_energySnap)
            ofs << e.round << "," << e.node << ","
                << std::fixed << std::setprecision (6) << e.residual << ","
                << e.pct << "\n";
    }

    std::cout << "Results: " << RESULTS_DIR << "\n";
    std::cout << "NetAnim: " << animFile << "\n";

    g_anim = nullptr;
    g_energy.clear ();
    g_sinkNode = nullptr;
    Simulator::Destroy ();
    return 0;
}
