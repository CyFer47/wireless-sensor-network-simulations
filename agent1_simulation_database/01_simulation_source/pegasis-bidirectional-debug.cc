/* =======================================================================
 *  pegasis-level1.2-sim.cc
 *
 *  PEGASIS (Power-Efficient GAthering in Sensor Information Systems)
 *  Level-1 Micro-Simulation for NS-3  —  Simulation V1.2  (revised)
 *  -------------------------------------------------------------------
 *  Three critical fixes applied over the original V1.2:
 *
 *    FIX 1 – NetAnim logical topology
 *      Chain-neighbour links and leader→sink links are injected into the
 *      animation XML via post-processing.  Current-round leader is
 *      highlighted in red through UpdateNodeColor().
 *
 *    FIX 2 – Theoretical First-Order Radio Model energy
 *      WifiRadioEnergyModel is NOT installed; idle-listening drain is
 *      eliminated.  Energy is tracked manually using:
 *        Etx(L,d) = Eelec·L + Efs·L·d²      [free-space, d < d0≈87.7 m]
 *        Erx(L)   = Eelec·L
 *        Eda(L)   = Eda·L                     [data aggregation at relay]
 *
 *    FIX 3 – Chain starts from the node FURTHEST from the sink
 *      (per Lindsey / Raghavendra original PEGASIS paper).
 *
 *  Parameters (unchanged from original V1.2):
 *    • 20 sensor nodes + 1 sink in a 50 m × 50 m area
 *    • Sink at (25.0, 25.0)
 *    • 5 rounds, 30 s/round (5 s setup + 25 s steady-state)
 *    • 2 data slots per round (DATA_INTERVAL = 10 s)
 *    • Initial energy: 2.0 J per sensor
 *    • Chain-based: greedy nearest-neighbour chain, leader rotation
 *    • Member → neighbour: 64-byte payload, 0.1 s hop spacing
 *    • Leader → Sink: 128-byte aggregated payload
 *
 *  Build & run:
 *      cp "<VM_WORKSPACE_PATH>/Simulation V1.2/pegasis-level1.2-sim.cc" scratch/
 *      ./ns3 build scratch/pegasis-level1.2-sim
 *      ./ns3 run scratch/pegasis-level1.2-sim
 *
 *  CSV outputs (timestamped sub-folder under results/):
 *      pegasis_round_summary.csv  – round,numLinks,leaderNodeId,chainToSinkPkts,chainMemberPkts
 *      pegasis_energy.csv         – round,nodeId,initialEnergy,residualEnergy,remainingPct
 *      pegasis_sink_packets.csv   – time,round,srcNodeId,seqNo
 *      pegasis_node_positions.csv – nodeId,role,x,y
 * ======================================================================= */

#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/internet-module.h"
#include "ns3/wifi-module.h"
#include "ns3/mobility-module.h"
#include "ns3/energy-module.h"
#include "ns3/netanim-module.h"

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
#include <cfloat>
#include <cassert>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE ("PegasisLevel1Sim");

/* =====================================================================
 *  Simulation Constants  (matched to MATLAB script)
 * ===================================================================== */
static const uint32_t NUM_SENSORS     = 20;        // sensor nodes
static const double   AREA_WIDTH      = 50.0;      // metres
static const double   AREA_HEIGHT     = 50.0;      // metres
static const double   ROUND_DURATION  = 30.0;      // seconds per round
static const double   SETUP_DURATION  = 5.0;       // seconds for the set-up phase
static const double   DATA_INTERVAL   = 10.0;      // seconds between data sends → 2 slots/round
static const uint32_t NUM_ROUNDS      = 5;         // total PEGASIS rounds (Level-1)
static const double   INITIAL_ENERGY  = 2.0;       // Joules per sensor
static const uint16_t SINK_PORT       = 9;         // UDP port: Leader → Sink
static const uint16_t CHAIN_PORT      = 10;        // UDP port: neighbour → neighbour on chain
static const uint16_t ACK_PORT        = 11;        // UDP port: Sink ACK → leader
static const double   COMM_RANGE      = 60.0;      // metres – WiFi communication range

/* =====================================================================
 *  First-Order Radio Model Constants  (Heinzelman et al.)
 *  -------------------------------------------------------------------
 *  Etx(L,d) = Eelec·L + Efs·L·d²         [free-space, d < d0 ≈ 87.7 m]
 *  Erx(L)   = Eelec·L
 *  Eda(L)   = Eda_per_bit·L               [data aggregation at relay]
 * ===================================================================== */
static const double E_ELEC      = 50.0e-9;     // 50  nJ/bit   (electronics)
static const double E_FS        = 10.0e-12;    // 10  pJ/bit/m²(free-space amp)
static const double E_DA_PERBIT = 5.0e-9;      //  5  nJ/bit   (data aggregation)

/** Base results directory.  Each run creates a timestamped sub-folder. */
static const std::string RESULTS_BASE =
    "<VM_HOME_PATH>/ns-allinone-3.42/ns-3.42/results";

/** Build a unique sub-folder: RESULTS_BASE/pegasis_YYYY-MM-DD_HH-MM-SS */
static std::string
MakeResultsDir ()
{
    auto now  = std::chrono::system_clock::now ();
    auto tt   = std::chrono::system_clock::to_time_t (now);
    std::tm   tm{};
    localtime_r (&tt, &tm);
    char buf[64];
    std::strftime (buf, sizeof (buf), "%Y-%m-%d_%H-%M-%S", &tm);
    return RESULTS_BASE + "/pegasis_" + std::string (buf);
}

/** Filled once at start of main(). */
static std::string RESULTS_DIR;

/* =====================================================================
 *  Global State & Metrics
 * ===================================================================== */

/** Per-round record (for summary CSV and end-of-sim report). */
struct RoundRecord
{
    uint32_t roundNumber;
    uint32_t leaderNodeId;
    uint32_t chainMemberPkts;   // total chain hop transmissions this round
    uint32_t chainToSinkPkts;   // leader → sink transmissions (1 per slot)
};
static std::vector<RoundRecord> g_roundRecords;

/** Per-packet record at the sink (for pegasis_sink_packets.csv). */
struct SinkPktRecord
{
    double   time;        // simulation time of reception
    uint32_t round;       // PEGASIS round number
    uint32_t srcNodeId;   // leader node ID
    uint32_t seqNo;       // global sequence number
};
static std::vector<SinkPktRecord> g_sinkPktLog;

/** Per-round per-node energy snapshot (for pegasis_energy.csv). */
struct EnergySnapshot
{
    uint32_t round;
    uint32_t nodeId;
    double   initialEnergy;
    double   residualEnergy;
    double   remainingPct;
};
static std::vector<EnergySnapshot> g_energySnapshots;

static uint32_t g_sinkPktRx             = 0;   // total packets received at sink
static uint32_t g_chainMemberPktTx      = 0;   // chain hop packets sent (cumulative)
static uint32_t g_leaderToSinkPktTx     = 0;   // leader → sink packets sent (cumulative)
static uint32_t g_currentRound          = 0;   // current PEGASIS round
static uint32_t g_sinkPktRxAtRoundStart = 0;   // for per-round packet delta
static uint32_t g_chainPktAtRoundStart  = 0;   // for per-round chain hop delta

static NodeContainer                              g_sensorNodes;
static Ptr<Node>                                  g_sinkNode;
static Ipv4InterfaceContainer                     g_allIfaces;        // 0..19 sensors, 20 sink
static std::vector<Ptr<energy::EnergySource>>     g_energySources;    // 0..19 sensors

/** Theoretical energy remaining per sensor (First-Order Radio Model).
 *  FIX 2 – bypasses NS-3 WifiRadioEnergyModel. */
static std::vector<double>                        g_nodeEnergy;

/** Global AnimationInterface pointer for per-round leader highlighting.
 *  Valid only while the AnimationInterface scope in main() is alive. */
static AnimationInterface*                        g_anim = nullptr;

/* =====================================================================
 *  Utility Helpers
 * ===================================================================== */

/** Return the 2-D position of an ns-3 node. */
static Vector
GetPos (Ptr<Node> n)
{
    return n->GetObject<MobilityModel> ()->GetPosition ();
}

/** Euclidean distance between two node IDs (0..19 = sensor, 20 = sink). */
static double
NodeDist (uint32_t a, uint32_t b)
{
    Ptr<Node> na = (a < NUM_SENSORS) ? g_sensorNodes.Get (a) : g_sinkNode;
    Ptr<Node> nb = (b < NUM_SENSORS) ? g_sensorNodes.Get (b) : g_sinkNode;
    Vector pa = GetPos (na);
    Vector pb = GetPos (nb);
    return std::sqrt ((pa.x - pb.x) * (pa.x - pb.x) +
                      (pa.y - pb.y) * (pa.y - pb.y));
}

/** Resolve an IPv4 address back to a sensor node ID (0..19).
 *  Returns UINT32_MAX if not found. */
static uint32_t
IpToNodeId (Ipv4Address addr)
{
    for (uint32_t i = 0; i < g_allIfaces.GetN (); ++i)
    {
        if (g_allIfaces.GetAddress (i) == addr)
            return i;
    }
    return UINT32_MAX;
}

/* =====================================================================
 *  FIX 2 – First-Order Radio Model energy deduction helpers
 * ===================================================================== */

/** Deduct transmit energy: Eelec·L + Efs·L·d² */
static void
DeductTxEnergy (uint32_t nodeId, uint32_t bits, double distMetres)
{
    double e = E_ELEC * bits + E_FS * bits * distMetres * distMetres;
    g_nodeEnergy[nodeId] = std::max (0.0, g_nodeEnergy[nodeId] - e);
}

/** Deduct receive energy: Eelec·L */
static void
DeductRxEnergy (uint32_t nodeId, uint32_t bits)
{
    double e = E_ELEC * bits;
    g_nodeEnergy[nodeId] = std::max (0.0, g_nodeEnergy[nodeId] - e);
}

/** Deduct data-aggregation energy at a relay / leader: Eda·L */
static void
DeductAggEnergy (uint32_t nodeId, uint32_t bits)
{
    double e = E_DA_PERBIT * bits;
    g_nodeEnergy[nodeId] = std::max (0.0, g_nodeEnergy[nodeId] - e);
}

/* =====================================================================
 *  Forward-declared free functions
 * ===================================================================== */
static void ChainHopSend    (uint32_t fromId, uint32_t toId);
static void LeaderSendToSink (uint32_t leaderId);
static void SinkSetupBroadcast (uint32_t roundNum);
static void EndOfRound       (uint32_t roundNum);

/* =====================================================================
 *  PegasisProtocol
 *  ———————————————
 *  PEGASIS (Power-Efficient GAthering in Sensor Information Systems)
 *
 *  1. Chain construction (once, at initialisation):
 *     – FIX 3: Greedy nearest-neighbour starting from the node
 *       FURTHEST from the sink (per Lindsey / Raghavendra paper).
 *
 *  2. Per round:
 *     – Leader = chain[round % chainLength]  (simple rotation).
 *     – FIX 1: Leader highlighted red in NetAnim.
 *     – Data forwarding: nodes on both sides of the leader forward
 *       64-byte packets hop-by-hop toward the leader along the chain.
 *     – Leader sends one 128-byte aggregated packet to the sink.
 *
 *  3. Timing (per data slot, 2 slots per round):
 *     – Chain hops are spaced 0.1 s apart from the chain ends inward.
 *     – Leader → Sink at the end after all hops.
 * ===================================================================== */
class PegasisProtocol
{
public:
    PegasisProtocol ();
    void Initialise ();
    void StartRound (uint32_t roundNum);

    /** Access the chain (for logging / NetAnim post-processing). */
    const std::vector<uint32_t> & GetChain () const { return m_chain; }

private:
    void BuildChain ();
    void ScheduleDataPhase ();

    /** Schedules one data slot of chain forwarding.
     *  @param slotBase  time offset from start of data phase. */
    void ScheduleSlot (double slotBase);

    std::vector<uint32_t>                m_chain;       // ordered chain of node IDs
    std::map<uint32_t, int>              m_chainPos;    // nodeId → position in chain
    uint32_t                             m_leaderIdx;   // chain index of this round's leader
    uint32_t                             m_leaderNode;  // node ID of this round's leader
};

static PegasisProtocol g_pegasis;

// --------------------------------------------------------------------- //
PegasisProtocol::PegasisProtocol ()
    : m_leaderIdx (0), m_leaderNode (0)
{
}

void
PegasisProtocol::Initialise ()
{
    BuildChain ();
}

// --------------------------------------------------------------------- //
//  FIX 3 – Greedy nearest-neighbour chain construction.
//
//  1. Start from the sensor node FURTHEST from the sink (25,25),
//     as specified in the original Lindsey / Raghavendra PEGASIS paper.
//  2. Repeatedly append the nearest unvisited sensor node.
//  3. Result: m_chain = ordered vector covering all NUM_SENSORS nodes.
// --------------------------------------------------------------------- //
void
PegasisProtocol::BuildChain ()
{
    NS_LOG_INFO ("[PEGASIS] Building greedy nearest-neighbour chain "
                 "(starting from furthest node) …");

    std::vector<bool> visited (NUM_SENSORS, false);
    m_chain.clear ();
    m_chainPos.clear ();

    /* ---- FIX 3: Find the sensor FURTHEST from the sink ---- */
    double   bestDist  = 0.0;
    uint32_t startNode = 0;
    for (uint32_t i = 0; i < NUM_SENSORS; ++i)
    {
        double d = NodeDist (i, NUM_SENSORS);   // distance to sink
        if (d > bestDist)
        {
            bestDist  = d;
            startNode = i;
        }
    }

    m_chain.push_back (startNode);
    visited[startNode] = true;
    NS_LOG_INFO ("[PEGASIS]   Chain[0] = Node " << startNode
                 << "  (furthest from sink, dist="
                 << std::fixed << std::setprecision (1) << bestDist << " m)");

    /* Greedy extension: always append nearest unvisited node. */
    for (uint32_t step = 1; step < NUM_SENSORS; ++step)
    {
        uint32_t last    = m_chain.back ();
        double   minDist = 1e12;
        uint32_t nextNode = UINT32_MAX;

        for (uint32_t j = 0; j < NUM_SENSORS; ++j)
        {
            if (visited[j])
                continue;
            double d = NodeDist (last, j);
            if (d < minDist)
            {
                minDist  = d;
                nextNode = j;
            }
        }

        assert (nextNode != UINT32_MAX);
        m_chain.push_back (nextNode);
        visited[nextNode] = true;
        NS_LOG_INFO ("[PEGASIS]   Chain[" << step << "] = Node " << nextNode
                     << "  (dist from " << last << " = "
                     << std::fixed << std::setprecision (1) << minDist << " m)");
    }

    /* Build position map. */
    for (uint32_t pos = 0; pos < m_chain.size (); ++pos)
        m_chainPos[m_chain[pos]] = static_cast<int> (pos);

    /* Sanity check. */
    assert (m_chain.size () == NUM_SENSORS);
    NS_LOG_INFO ("[PEGASIS] Chain complete: " << m_chain.size () << " nodes.");

    /* Print the chain. */
    std::ostringstream oss;
    for (uint32_t i = 0; i < m_chain.size (); ++i)
    {
        if (i > 0) oss << " → ";
        oss << m_chain[i];
    }
    NS_LOG_INFO ("[PEGASIS] Chain order: " << oss.str ());
}

// --------------------------------------------------------------------- //
void
PegasisProtocol::StartRound (uint32_t roundNum)
{
    g_currentRound          = roundNum;
    g_sinkPktRxAtRoundStart = g_sinkPktRx;
    g_chainPktAtRoundStart  = g_chainMemberPktTx;

    NS_LOG_INFO ("\n========== ROUND " << roundNum
                 << "  (t=" << Simulator::Now ().GetSeconds () << " s) ==========");

    /* Leader selection: simple rotation along the chain. */
    m_leaderIdx  = roundNum % static_cast<uint32_t> (m_chain.size ());
    m_leaderNode = m_chain[m_leaderIdx];

    NS_LOG_INFO ("[PEGASIS] Leader this round: Node " << m_leaderNode
                 << "  (chain position " << m_leaderIdx << ")");

    /* FIX 1 – Highlight current leader in NetAnim (orange). */
    if (g_anim)
    {
        /* Reset all sensors to green first. */
        for (uint32_t i = 0; i < NUM_SENSORS; ++i)
            g_anim->UpdateNodeColor (g_sensorNodes.Get (i), 0, 200, 0);
        /* Leader → orange. */
        g_anim->UpdateNodeColor (g_sensorNodes.Get (m_leaderNode), 255, 165, 0);
    }

    /* Setup phase visual cue: sink broadcasts setup packet to sensors. */
    Simulator::Schedule (Seconds (0.2), &SinkSetupBroadcast, roundNum);

    /* Schedule steady-state data phase after setup delay. */
    Simulator::Schedule (Seconds (SETUP_DURATION),
                         &PegasisProtocol::ScheduleDataPhase, this);
}

// --------------------------------------------------------------------- //
//  Steady-State Data Phase
//
//  2 data slots per round (DATA_INTERVAL = 10 s).
//  In each slot, chain nodes forward data hop-by-hop toward the leader.
// --------------------------------------------------------------------- //
void
PegasisProtocol::ScheduleDataPhase ()
{
    NS_LOG_INFO ("[STEADY] Data phase starts at t="
                 << Simulator::Now ().GetSeconds () << " s");

    double   steadyLen = ROUND_DURATION - SETUP_DURATION;   // 25 s
    uint32_t numSlots  = static_cast<uint32_t> (steadyLen / DATA_INTERVAL);  // 2

    for (uint32_t s = 0; s < numSlots; ++s)
    {
        double base = s * DATA_INTERVAL;
        ScheduleSlot (base);
    }
}

// --------------------------------------------------------------------- //
//  Schedule one data-aggregation slot.
//
//  The leader sits at chain position m_leaderIdx.
//  – Left arm: nodes at positions 0 .. leaderIdx−1 forward right
//    (toward the leader), starting from the far end (pos 0).
//  – Right arm: nodes at positions leaderIdx+1 .. N−1 forward left
//    (toward the leader), starting from the far end (pos N−1).
//  – Hops are spaced 0.1 s apart.
//  – After all chain hops, the leader sends to the sink.
// --------------------------------------------------------------------- //
void
PegasisProtocol::ScheduleSlot (double slotBase)
{
    uint32_t N     = static_cast<uint32_t> (m_chain.size ());
    uint32_t lIdx  = m_leaderIdx;
    double   hop   = 0.1;   // seconds between consecutive hops
    uint32_t hopCount = 0;

    /* ---- Left arm: pos 0 → 1 → … → lIdx-1 → lIdx (leader) ---- */
    for (uint32_t pos = 0; pos < lIdx; ++pos)
    {
        uint32_t from = m_chain[pos];
        uint32_t to   = m_chain[pos + 1];
        double   delay = slotBase + hopCount * hop;
        Simulator::Schedule (Seconds (delay),
                             &ChainHopSend, from, to);
        ++hopCount;
    }

    /* ---- Right arm: pos N-1 → N-2 → … → lIdx+1 → lIdx (leader) ---- */
    for (uint32_t pos = N - 1; pos > lIdx; --pos)
    {
        uint32_t from = m_chain[pos];
        uint32_t to   = m_chain[pos - 1];
        double   delay = slotBase + hopCount * hop;
        Simulator::Schedule (Seconds (delay),
                             &ChainHopSend, from, to);
        ++hopCount;
    }

    /* ---- Leader → Sink (after all hops) ---- */
    double leaderDelay = slotBase + hopCount * hop + 0.2;
    Simulator::Schedule (Seconds (leaderDelay),
                         &LeaderSendToSink, m_leaderNode);
}

/* =====================================================================
 *  Data-Phase Free Functions  (with FIX 2 – energy deduction)
 * ===================================================================== */

/** Chain node sends a 64-byte UDP packet to its chain neighbour.
 *  FIX 2: Deducts theoretical Tx, Rx, and aggregation energy. */
static void
ChainHopSend (uint32_t fromId, uint32_t toId)
{
    /* ---- WiFi packet (keeps NS-3 connectivity + NetAnim trace) ---- */
    Ptr<Node>    fromNode = g_sensorNodes.Get (fromId);
    Ipv4Address  toAddr   = g_allIfaces.GetAddress (toId);

    Ptr<Socket> sock = Socket::CreateSocket (fromNode,
                           TypeId::LookupByName ("ns3::UdpSocketFactory"));
    sock->Connect (InetSocketAddress (toAddr, CHAIN_PORT));
    Ptr<Packet> pkt = Create<Packet> (64);       // 64 B payload
    sock->Send (pkt);
    sock->Close ();

    /* ---- FIX 2: Theoretical energy deduction ---- */
    double   dist = NodeDist (fromId, toId);
    uint32_t bits = 64 * 8;                      // 64 bytes = 512 bits
    DeductTxEnergy  (fromId, bits, dist);         // sender   Tx
    DeductRxEnergy  (toId,   bits);               // receiver Rx
    DeductAggEnergy (toId,   bits);               // receiver data aggregation

    ++g_chainMemberPktTx;
    NS_LOG_INFO ("[CHAIN]  t=" << Simulator::Now ().GetSeconds ()
                 << " s  Node " << fromId << " ──► Node " << toId
                 << "  (d=" << std::fixed << std::setprecision (1)
                 << dist << " m)");
}

/** Leader aggregates data into a 128-byte packet and sends to the sink.
 *  FIX 2: Deducts theoretical Tx and aggregation energy from leader. */
static void
LeaderSendToSink (uint32_t leaderId)
{
    Ptr<Node>    leaderNode = g_sensorNodes.Get (leaderId);
    Ipv4Address  sinkAddr   = g_allIfaces.GetAddress (NUM_SENSORS);

    Ptr<Socket> sock = Socket::CreateSocket (leaderNode,
                           TypeId::LookupByName ("ns3::UdpSocketFactory"));
    sock->Connect (InetSocketAddress (sinkAddr, SINK_PORT));
    Ptr<Packet> pkt = Create<Packet> (128);      // 128 B aggregated
    sock->Send (pkt);
    sock->Close ();

    /* ---- FIX 2: Theoretical energy deduction ---- */
    double   dist = NodeDist (leaderId, NUM_SENSORS);
    uint32_t bits = 128 * 8;                     // 128 bytes = 1024 bits
    DeductTxEnergy  (leaderId, bits, dist);       // leader Tx to sink
    DeductAggEnergy (leaderId, bits);             // leader final aggregation

    ++g_leaderToSinkPktTx;
    NS_LOG_INFO ("[AGGR]   t=" << Simulator::Now ().GetSeconds ()
                 << " s  Leader " << leaderId << " ──► Sink"
                 << "  (d=" << std::fixed << std::setprecision (1)
                 << dist << " m)");
    NS_LOG_UNCOND ("Round " << g_currentRound << ": Leader " << leaderId << "->sink agg pkt");
}

static void
SinkSetupBroadcast (uint32_t roundNum)
{
    for (uint32_t i = 0; i < NUM_SENSORS; ++i)
    {
        Ptr<Socket> s = Socket::CreateSocket (g_sinkNode,
                           TypeId::LookupByName ("ns3::UdpSocketFactory"));
        s->Connect (InetSocketAddress (g_allIfaces.GetAddress (i), CHAIN_PORT));
        Ptr<Packet> p = Create<Packet> (32);
        s->Send (p);
        s->Close ();
    }
    NS_LOG_INFO ("[SETUP] Round " << roundNum << " sink setup broadcast/unicast complete");
}

/* =====================================================================
 *  EndOfRound – scheduled at (round+1)*ROUND_DURATION − 0.01 s
 *
 *  1) Snapshots per-node energy from g_nodeEnergy[] (FIX 2)
 *  2) Prints per-round summary line to stdout
 *  3) Records round data for CSV
 * ===================================================================== */
static void
EndOfRound (uint32_t roundNum)
{
    /* ---- Energy snapshot (one row per node per round) ---- */
    for (uint32_t i = 0; i < NUM_SENSORS; ++i)
    {
        double rem = g_nodeEnergy[i];
        EnergySnapshot snap;
        snap.round          = roundNum;
        snap.nodeId         = i;
        snap.initialEnergy  = INITIAL_ENERGY;
        snap.residualEnergy = rem;
        snap.remainingPct   = 100.0 * rem / INITIAL_ENERGY;
        g_energySnapshots.push_back (snap);
    }

    /* ---- Per-round metrics ---- */
    uint32_t sinkThisRound  = g_sinkPktRx - g_sinkPktRxAtRoundStart;
    uint32_t chainThisRound = g_chainMemberPktTx - g_chainPktAtRoundStart;

    /* Determine this round's leader from the chain. */
    const auto &chain = g_pegasis.GetChain ();
    uint32_t leaderIdx  = roundNum % static_cast<uint32_t> (chain.size ());
    uint32_t leaderNode = chain[leaderIdx];

    RoundRecord rec;
    rec.roundNumber     = roundNum;
    rec.leaderNodeId    = leaderNode;
    rec.chainMemberPkts = chainThisRound;
    rec.chainToSinkPkts = sinkThisRound;
    g_roundRecords.push_back (rec);

    /* Average theoretical energy remaining. */
    double totalRem = 0.0;
    for (uint32_t i = 0; i < NUM_SENSORS; ++i)
        totalRem += g_nodeEnergy[i];
    double avgRem = totalRem / NUM_SENSORS;

    std::cout << "[ROUND " << roundNum << "]"
              << "  Leader=" << leaderNode
              << "  ChainHops=" << chainThisRound
              << "  SinkPkts=" << sinkThisRound
              << "  AvgEnergy=" << std::fixed << std::setprecision (6)
              << avgRem << " J\n";
}

/* =====================================================================
 *  SinkApp – UDP receiver on the sink node
 * ===================================================================== */
class SinkApp : public Application
{
public:
    static TypeId GetTypeId ();
    SinkApp ()  : m_socket (nullptr) {}
    ~SinkApp () override { m_socket = nullptr; }

protected:
    void StartApplication () override;
    void StopApplication  () override;

private:
    void HandleRead (Ptr<Socket> socket);
    Ptr<Socket> m_socket;
};

NS_OBJECT_ENSURE_REGISTERED (SinkApp);

TypeId
SinkApp::GetTypeId ()
{
    static TypeId tid = TypeId ("ns3::SinkApp")
        .SetParent<Application> ()
        .SetGroupName ("Applications")
        .AddConstructor<SinkApp> ();
    return tid;
}

void
SinkApp::StartApplication ()
{
    if (!m_socket)
    {
        m_socket = Socket::CreateSocket (GetNode (),
                       TypeId::LookupByName ("ns3::UdpSocketFactory"));
        m_socket->Bind (InetSocketAddress (Ipv4Address::GetAny (), SINK_PORT));
    }
    m_socket->SetRecvCallback (MakeCallback (&SinkApp::HandleRead, this));
}

void
SinkApp::StopApplication ()
{
    if (m_socket)
    {
        m_socket->Close ();
        m_socket->SetRecvCallback (MakeNullCallback<void, Ptr<Socket>> ());
    }
}

void
SinkApp::HandleRead (Ptr<Socket> socket)
{
    Ptr<Packet> pkt;
    Address     from;
    while ((pkt = socket->RecvFrom (from)))
    {
        ++g_sinkPktRx;

        Ipv4Address srcIp   = InetSocketAddress::ConvertFrom (from).GetIpv4 ();
        uint32_t    srcNode = IpToNodeId (srcIp);

        SinkPktRecord rec;
        rec.time      = Simulator::Now ().GetSeconds ();
        rec.round     = g_currentRound;
        rec.srcNodeId = srcNode;
        rec.seqNo     = g_sinkPktRx;           // global sequence number
        g_sinkPktLog.push_back (rec);

        NS_LOG_INFO ("[SINK]   Pkt #" << g_sinkPktRx
                     << "  from Node " << srcNode
                     << " (" << srcIp << ")"
                     << "  round=" << g_currentRound
                     << "  size=" << pkt->GetSize () << " B");

        /* ACK back to leader for explicit reverse-direction arrows in NetAnim. */
        if (srcNode < NUM_SENSORS)
        {
            Ptr<Socket> ack = Socket::CreateSocket (g_sinkNode,
                               TypeId::LookupByName ("ns3::UdpSocketFactory"));
            ack->Connect (InetSocketAddress (srcIp, ACK_PORT));
            Ptr<Packet> ackPkt = Create<Packet> (24);
            ack->Send (ackPkt);
            ack->Close ();
            NS_LOG_INFO ("[ACK]    Sink ──► Leader " << srcNode << "  size=24 B");
        }
    }
}

/* =====================================================================
 *  ChainReceiverApp – UDP receiver on every sensor node (CHAIN_PORT)
 * ===================================================================== */
class ChainReceiverApp : public Application
{
public:
    static TypeId GetTypeId ();
    ChainReceiverApp ()  : m_socket (nullptr) {}
    ~ChainReceiverApp () override { m_socket = nullptr; }

protected:
    void StartApplication () override;
    void StopApplication  () override;

private:
    void HandleRead (Ptr<Socket> socket);
    Ptr<Socket> m_socket;
};

NS_OBJECT_ENSURE_REGISTERED (ChainReceiverApp);

class AckReceiverApp : public Application
{
public:
    static TypeId GetTypeId ();
    AckReceiverApp () : m_socket (nullptr) {}
    ~AckReceiverApp () override { m_socket = nullptr; }

protected:
    void StartApplication () override;
    void StopApplication  () override;

private:
    void HandleRead (Ptr<Socket> socket);
    Ptr<Socket> m_socket;
};

NS_OBJECT_ENSURE_REGISTERED (AckReceiverApp);

TypeId
AckReceiverApp::GetTypeId ()
{
    static TypeId tid = TypeId ("ns3::AckReceiverApp")
        .SetParent<Application> ()
        .SetGroupName ("Applications")
        .AddConstructor<AckReceiverApp> ();
    return tid;
}

void
AckReceiverApp::StartApplication ()
{
    if (!m_socket)
    {
        m_socket = Socket::CreateSocket (GetNode (),
                       TypeId::LookupByName ("ns3::UdpSocketFactory"));
        m_socket->Bind (InetSocketAddress (Ipv4Address::GetAny (), ACK_PORT));
    }
    m_socket->SetRecvCallback (MakeCallback (&AckReceiverApp::HandleRead, this));
}

void
AckReceiverApp::StopApplication ()
{
    if (m_socket)
    {
        m_socket->Close ();
        m_socket->SetRecvCallback (MakeNullCallback<void, Ptr<Socket>> ());
    }
}

void
AckReceiverApp::HandleRead (Ptr<Socket> socket)
{
    Ptr<Packet> pkt;
    Address from;
    while ((pkt = socket->RecvFrom (from)))
    {
        NS_LOG_INFO ("[ACK-RX] Node " << GetNode ()->GetId ()
                     << " ◄── " << InetSocketAddress::ConvertFrom (from).GetIpv4 ()
                     << " size=" << pkt->GetSize () << " B");
    }
}

TypeId
ChainReceiverApp::GetTypeId ()
{
    static TypeId tid = TypeId ("ns3::ChainReceiverApp")
        .SetParent<Application> ()
        .SetGroupName ("Applications")
        .AddConstructor<ChainReceiverApp> ();
    return tid;
}

void
ChainReceiverApp::StartApplication ()
{
    if (!m_socket)
    {
        m_socket = Socket::CreateSocket (GetNode (),
                       TypeId::LookupByName ("ns3::UdpSocketFactory"));
        m_socket->Bind (InetSocketAddress (Ipv4Address::GetAny (), CHAIN_PORT));
    }
    m_socket->SetRecvCallback (MakeCallback (&ChainReceiverApp::HandleRead, this));
}

void
ChainReceiverApp::StopApplication ()
{
    if (m_socket)
    {
        m_socket->Close ();
        m_socket->SetRecvCallback (MakeNullCallback<void, Ptr<Socket>> ());
    }
}

void
ChainReceiverApp::HandleRead (Ptr<Socket> socket)
{
    Ptr<Packet> pkt;
    Address     from;
    while ((pkt = socket->RecvFrom (from)))
    {
        NS_LOG_INFO ("[CHAIN-RX]  Node " << GetNode ()->GetId ()
                     << " ◄── " << InetSocketAddress::ConvertFrom (from).GetIpv4 ()
                     << "  size=" << pkt->GetSize () << " B");
    }
}

/* =====================================================================
 *  PrintResults – end-of-simulation summary  (uses g_nodeEnergy, FIX 2)
 * ===================================================================== */
static void
PrintResults ()
{
    std::cout << "\n" << std::string (65, '=')
              << "\n          PEGASIS Level-1 Simulation Complete\n"
              << std::string (65, '=') << "\n";

    std::cout << "\n  Total packets received at sink : " << g_sinkPktRx << "\n";

    double totalRemaining = 0.0;
    for (uint32_t i = 0; i < NUM_SENSORS; ++i)
        totalRemaining += g_nodeEnergy[i];
    double avgRemaining = totalRemaining / NUM_SENSORS;

    std::cout << "  Average remaining energy       : "
              << std::fixed << std::setprecision (6) << avgRemaining << " J  ("
              << std::setprecision (2) << (100.0 * avgRemaining / INITIAL_ENERGY)
              << " %)\n";

    /* Per-node energy table. */
    std::cout << "\n  Per-node remaining energy (First-Order Radio Model):\n";
    for (uint32_t i = 0; i < NUM_SENSORS; ++i)
    {
        double pct = 100.0 * g_nodeEnergy[i] / INITIAL_ENERGY;
        std::cout << "    Node " << std::setw (2) << i << ": "
                  << std::fixed << std::setprecision (6)
                  << g_nodeEnergy[i] << " J  ("
                  << std::setprecision (4) << pct << " %)\n";
    }

    std::cout << "\n" << std::string (65, '=') << "\n\n";
}

/* =====================================================================
 *  ExportResultsCSV – MATLAB-aligned CSV files
 *
 *  Schema is unchanged from original V1.2; values now reflect the
 *  theoretical First-Order Radio Model (FIX 2).
 *
 *  1. pegasis_round_summary.csv  – round,numLinks,leaderNodeId,chainToSinkPkts,chainMemberPkts
 *  2. pegasis_energy.csv         – round,nodeId,initialEnergy,residualEnergy,remainingPct
 *  3. pegasis_sink_packets.csv   – time,round,srcNodeId,seqNo
 *  4. pegasis_node_positions.csv – nodeId,role,x,y
 * ===================================================================== */
static void
ExportResultsCSV ()
{
    std::filesystem::create_directories (RESULTS_DIR);

    /* ---- 1. pegasis_round_summary.csv ---- */
    {
        std::string path = RESULTS_DIR + "/pegasis_round_summary.csv";
        std::ofstream ofs (path);
        ofs << "round,numLinks,leaderNodeId,chainToSinkPkts,chainMemberPkts\n";

        for (const auto &rec : g_roundRecords)
        {
            ofs << rec.roundNumber << ","
                << (NUM_SENSORS - 1) << ","
                << rec.leaderNodeId << ","
                << rec.chainToSinkPkts << ","
                << rec.chainMemberPkts << "\n";
        }
        ofs.close ();
        std::cout << "[CSV] Written: " << path << "\n";
    }

    /* ---- 2. pegasis_energy.csv (per-round, per-node) ---- */
    {
        std::string path = RESULTS_DIR + "/pegasis_energy.csv";
        std::ofstream ofs (path);
        ofs << "round,nodeId,initialEnergy,residualEnergy,remainingPct\n";

        for (const auto &snap : g_energySnapshots)
        {
            ofs << snap.round << ","
                << snap.nodeId << ","
                << std::fixed << std::setprecision (6)
                << snap.initialEnergy << ","
                << snap.residualEnergy << ","
                << std::setprecision (4) << snap.remainingPct << "\n";
        }
        ofs.close ();
        std::cout << "[CSV] Written: " << path << "\n";
    }

    /* ---- 3. pegasis_sink_packets.csv (per-packet at sink) ---- */
    {
        std::string path = RESULTS_DIR + "/pegasis_sink_packets.csv";
        std::ofstream ofs (path);
        ofs << "time,round,srcNodeId,seqNo\n";

        for (const auto &pr : g_sinkPktLog)
        {
            ofs << std::fixed << std::setprecision (4)
                << pr.time << ","
                << pr.round << ","
                << pr.srcNodeId << ","
                << pr.seqNo << "\n";
        }
        ofs.close ();
        std::cout << "[CSV] Written: " << path << "\n";
    }

    /* ---- 4. pegasis_node_positions.csv ---- */
    {
        std::string path = RESULTS_DIR + "/pegasis_node_positions.csv";
        std::ofstream ofs (path);
        ofs << "nodeId,role,x,y\n";

        for (uint32_t i = 0; i < NUM_SENSORS; ++i)
        {
            Vector p = GetPos (g_sensorNodes.Get (i));
            ofs << i << ",sensor,"
                << std::fixed << std::setprecision (2)
                << p.x << "," << p.y << "\n";
        }
        Vector sp = GetPos (g_sinkNode);
        ofs << NUM_SENSORS << ",sink,"
            << std::fixed << std::setprecision (2)
            << sp.x << "," << sp.y << "\n";

        ofs.close ();
        std::cout << "[CSV] Written: " << path << "\n";
    }

    std::cout << "\n[CSV] All result files saved to: " << RESULTS_DIR << "/\n";
}

/* =====================================================================
 *  FIX 1 – Post-process NetAnim XML to inject chain topology links.
 *
 *  NetAnim shows WiFi as broadcast circles, not point-to-point lines.
 *  We inject <link> elements into the XML so NetAnim renders the
 *  PEGASIS chain structure and leader→sink connections as visible lines.
 *
 *  NOTE: Standard NetAnim XML does not support dashed-line styles;
 *  leader→sink links are drawn as regular lines with a descriptive
 *  label ("leader-sink").  The current leader is additionally
 *  highlighted in red via UpdateNodeColor in StartRound().
 * ===================================================================== */
static void
PostProcessNetAnimXml (const std::string &xmlFile,
                       const std::vector<uint32_t> &chain)
{
    /* Read the entire animation XML into memory. */
    std::ifstream ifs (xmlFile);
    if (!ifs.is_open ())
    {
        std::cerr << "[WARN] Cannot open " << xmlFile
                  << " for post-processing.\n";
        return;
    }
    std::string content ((std::istreambuf_iterator<char> (ifs)),
                          std::istreambuf_iterator<char> ());
    ifs.close ();

    /* Build link XML elements. */
    std::ostringstream linkXml;
    linkXml << "<!-- ====== PEGASIS chain topology (injected) ====== -->\n";

    /* ---- Chain-neighbour links (19 links for 20 nodes) ---- */
    for (size_t i = 0; i + 1 < chain.size (); ++i)
    {
        linkXml << "<link fromId=\"" << chain[i]
                << "\" toId=\"" << chain[i + 1]
                << "\" fd=\"0\" td=\"0\" ld=\"\"/>\n";
    }

    /* ---- Leader → Sink links (one per unique leader across rounds) ---- */
    std::set<uint32_t> drawnLeaders;
    for (uint32_t r = 0; r < NUM_ROUNDS; ++r)
    {
        uint32_t lIdx = r % static_cast<uint32_t> (chain.size ());
        uint32_t lid  = chain[lIdx];
        if (drawnLeaders.count (lid))
            continue;                   // already drawn
        drawnLeaders.insert (lid);

        linkXml << "<link fromId=\"" << lid
                << "\" toId=\"" << NUM_SENSORS
                << "\" fd=\"0\" td=\"0\" ld=\"\"/>\n";
    }
    linkXml << "<!-- ================================================ -->\n";

    /* Insert the link elements just before the closing </anim> tag. */
    size_t pos = content.rfind ("</anim>");
    if (pos != std::string::npos)
        content.insert (pos, linkXml.str ());
    else
        std::cerr << "[WARN] </anim> tag not found in " << xmlFile << "\n";

    /* Write the modified XML back. */
    std::ofstream ofs (xmlFile, std::ios::trunc);
    ofs << content;
    ofs.close ();

    std::cout << "[NETANIM] " << (chain.size () - 1) << " chain links + "
              << drawnLeaders.size () << " leader→sink links injected into "
              << xmlFile << "\n";
}

/* =====================================================================
 *  main()
 * ===================================================================== */
int
main (int argc, char *argv[])
{
    /* ---------- 0.  Command-line & logging ---------- */
    LogComponentEnable ("PegasisLevel1Sim", LOG_LEVEL_INFO);

    CommandLine cmd (__FILE__);
    cmd.Parse (argc, argv);

    /* Create timestamped results folder. */
    RESULTS_DIR = MakeResultsDir ();
    std::filesystem::create_directories (RESULTS_DIR);

    NS_LOG_INFO ("PEGASIS Level-1 Micro-Simulation  (revised: 3 fixes)  |  "
                 << NUM_SENSORS << " sensors, "
                 << NUM_ROUNDS  << " rounds, "
                 << ROUND_DURATION << " s/round");
    NS_LOG_INFO ("[RESULTS] Output folder: " << RESULTS_DIR);

    /* ================================================================
     *  1.  Create Nodes   (0..19 = sensors, 20 = sink)
     * ================================================================ */
    g_sensorNodes.Create (NUM_SENSORS);
    NodeContainer sinkContainer;
    sinkContainer.Create (1);
    g_sinkNode = sinkContainer.Get (0);

    NodeContainer allNodes;
    allNodes.Add (g_sensorNodes);
    allNodes.Add (g_sinkNode);

    /* ================================================================
     *  2.  Position Nodes
     *      Sensors: uniformly random inside [2, 48] × [2, 48]
     *      Sink:    centre of the area at (25.0, 25.0)
     * ================================================================ */
    Ptr<ListPositionAllocator> posAlloc = CreateObject<ListPositionAllocator> ();

    Ptr<UniformRandomVariable> rngX = CreateObject<UniformRandomVariable> ();
    rngX->SetAttribute ("Min", DoubleValue (2.0));
    rngX->SetAttribute ("Max", DoubleValue (AREA_WIDTH - 2.0));
    Ptr<UniformRandomVariable> rngY = CreateObject<UniformRandomVariable> ();
    rngY->SetAttribute ("Min", DoubleValue (2.0));
    rngY->SetAttribute ("Max", DoubleValue (AREA_HEIGHT - 2.0));

    NS_LOG_INFO ("\nNode positions:");
    for (uint32_t i = 0; i < NUM_SENSORS; ++i)
    {
        double x = rngX->GetValue ();
        double y = rngY->GetValue ();
        posAlloc->Add (Vector (x, y, 0.0));
        NS_LOG_INFO ("  Sensor " << std::setw (2) << i
                     << " : (" << std::fixed << std::setprecision (1)
                     << x << ", " << y << ")");
    }
    posAlloc->Add (Vector (AREA_WIDTH / 2.0, AREA_HEIGHT / 2.0, 0.0));
    NS_LOG_INFO ("  Sink   " << NUM_SENSORS << " : (25.0, 25.0)");

    MobilityHelper mobility;
    mobility.SetPositionAllocator (posAlloc);
    mobility.SetMobilityModel ("ns3::ConstantPositionMobilityModel");
    mobility.Install (allNodes);

    /* ================================================================
     *  3.  WiFi PHY / MAC  (802.11b Ad-Hoc, fixed comm range)
     * ================================================================ */
    WifiHelper wifi;
    wifi.SetStandard (WIFI_STANDARD_80211b);
    wifi.SetRemoteStationManager ("ns3::ConstantRateWifiManager",
                                  "DataMode",    StringValue ("DsssRate1Mbps"),
                                  "ControlMode", StringValue ("DsssRate1Mbps"));

    YansWifiPhyHelper wifiPhy;
    YansWifiChannelHelper wifiChannel;
    wifiChannel.SetPropagationDelay ("ns3::ConstantSpeedPropagationDelayModel");
    wifiChannel.AddPropagationLoss  ("ns3::RangePropagationLossModel",
                                     "MaxRange", DoubleValue (COMM_RANGE));
    wifiPhy.SetChannel (wifiChannel.Create ());
    wifiPhy.Set ("TxPowerStart", DoubleValue (0.0));
    wifiPhy.Set ("TxPowerEnd",   DoubleValue (0.0));

    WifiMacHelper wifiMac;
    wifiMac.SetType ("ns3::AdhocWifiMac");

    NetDeviceContainer allDevices = wifi.Install (wifiPhy, wifiMac, allNodes);

    /* ================================================================
     *  4.  Internet Stack & IPv4
     * ================================================================ */
    InternetStackHelper internet;
    internet.Install (allNodes);

    Ipv4AddressHelper ipv4;
    ipv4.SetBase ("10.1.1.0", "255.255.255.0");
    g_allIfaces = ipv4.Assign (allDevices);

    NS_LOG_INFO ("\nIPv4 addresses:");
    for (uint32_t i = 0; i < allNodes.GetN (); ++i)
        NS_LOG_INFO ("  Node " << std::setw (2) << i
                     << " : " << g_allIfaces.GetAddress (i));

    /* ================================================================
     *  5.  Energy Model  (FIX 2 – theoretical, no WifiRadioEnergyModel)
     *
     *  BasicEnergySource is installed for NS-3 infrastructure, but
     *  WifiRadioEnergyModel is NOT attached.  This eliminates the
     *  idle-listening drain and fixed-TxPower assumptions.
     *
     *  All energy accounting uses the First-Order Radio Model via
     *  g_nodeEnergy[] (manually deducted on every send/receive).
     * ================================================================ */
    BasicEnergySourceHelper energySrcHelper;
    energySrcHelper.Set ("BasicEnergySourceInitialEnergyJ",
                         DoubleValue (INITIAL_ENERGY));
    energy::EnergySourceContainer esContainer =
        energySrcHelper.Install (g_sensorNodes);

    g_energySources.clear ();
    for (uint32_t i = 0; i < esContainer.GetN (); ++i)
        g_energySources.push_back (esContainer.Get (i));

    /* NO WifiRadioEnergyModel installed — idle/Tx/Rx drain bypassed. */

    /* Initialise theoretical energy vector. */
    g_nodeEnergy.assign (NUM_SENSORS, INITIAL_ENERGY);

    NS_LOG_INFO ("\nEnergy model: First-Order Radio (theoretical)");
    NS_LOG_INFO ("  Eelec = " << E_ELEC * 1e9  << " nJ/bit");
    NS_LOG_INFO ("  Efs   = " << E_FS   * 1e12 << " pJ/bit/m^2");
    NS_LOG_INFO ("  Eda   = " << E_DA_PERBIT * 1e9 << " nJ/bit");
    NS_LOG_INFO ("  Initial energy per sensor: " << INITIAL_ENERGY << " J");

    /* ================================================================
     *  6.  Install Receiver Applications
     * ================================================================ */
    double simEnd = NUM_ROUNDS * ROUND_DURATION + 10.0;

    Ptr<SinkApp> sinkApp = CreateObject<SinkApp> ();
    g_sinkNode->AddApplication (sinkApp);
    sinkApp->SetStartTime (Seconds (0.0));
    sinkApp->SetStopTime  (Seconds (simEnd));

    for (uint32_t i = 0; i < NUM_SENSORS; ++i)
    {
        Ptr<ChainReceiverApp> chainApp = CreateObject<ChainReceiverApp> ();
        g_sensorNodes.Get (i)->AddApplication (chainApp);
        chainApp->SetStartTime (Seconds (0.0));
        chainApp->SetStopTime  (Seconds (simEnd));

        Ptr<AckReceiverApp> ackApp = CreateObject<AckReceiverApp> ();
        g_sensorNodes.Get (i)->AddApplication (ackApp);
        ackApp->SetStartTime (Seconds (0.0));
        ackApp->SetStopTime  (Seconds (simEnd));
    }

    /* ================================================================
     *  7.  Initialise PEGASIS & Schedule Rounds + End-of-Round
     * ================================================================ */
    g_pegasis.Initialise ();
    for (uint32_t r = 0; r < NUM_ROUNDS; ++r)
    {
        /* Round start */
        Simulator::Schedule (Seconds (r * ROUND_DURATION),
                             &PegasisProtocol::StartRound, &g_pegasis, r);
        /* End-of-round energy snapshot + per-round stdout summary */
        Simulator::Schedule (Seconds ((r + 1) * ROUND_DURATION - 0.01),
                             &EndOfRound, r);
    }

    /* ================================================================
     *  8.  NetAnim + Simulation Run
     *
     *  The AnimationInterface lives in this scope block so that its
     *  destructor (which writes </anim>) runs before we post-process
     *  the XML file to inject chain topology links (FIX 1).
     * ================================================================ */
    std::string animFile = RESULTS_DIR + "/pegasis-anim.xml";

    {
        AnimationInterface anim (animFile);
        anim.SetMaxPktsPerTraceFile (500000);
        anim.SetMobilityPollInterval (Seconds (1.0));
        anim.EnablePacketMetadata (true);

        for (uint32_t i = 0; i < NUM_SENSORS; ++i)
        {
            anim.UpdateNodeDescription (g_sensorNodes.Get (i),
                                         "S" + std::to_string (i));
            anim.UpdateNodeColor (g_sensorNodes.Get (i), 0, 200, 0);   // green
            anim.UpdateNodeSize  (g_sensorNodes.Get (i), 2.0, 2.0);
        }
        anim.UpdateNodeDescription (g_sinkNode, "SINK");
        anim.UpdateNodeColor (g_sinkNode, 255, 0, 0);                  // red
        anim.UpdateNodeSize  (g_sinkNode, 3.0, 3.0);

        g_anim = &anim;    // expose to StartRound() for leader highlighting

        NS_LOG_INFO ("[NETANIM] Animation XML → " << animFile);

        /* ---- Run ---- */
        Simulator::Stop (Seconds (simEnd));
        NS_LOG_INFO ("\nSimulation: " << simEnd << " s\n");
        Simulator::Run ();

        g_anim = nullptr;
    }   // ~AnimationInterface writes </anim> and closes the file

    /* ================================================================
     *  9.  FIX 1 – Post-process NetAnim XML to inject chain links
     * ================================================================ */
    PostProcessNetAnimXml (animFile, g_pegasis.GetChain ());

    /* ================================================================
     *  10. Results
     * ================================================================ */
    PrintResults ();
    ExportResultsCSV ();

    std::cout << "[NETANIM] " << animFile << "\n"
              << "          Open with:  netanim " << animFile << "\n\n";

    g_energySources.clear ();
    g_sinkNode = nullptr;
    Simulator::Destroy ();
    return 0;
}
