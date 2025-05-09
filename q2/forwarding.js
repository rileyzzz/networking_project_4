
// i'm using the raw binary representation here instead of CIDR, because it's easier to see how the prefixes/matching works.
// The first three entries in the table are from the slides.
const fwdTable = [
    { prefix: "11001000 00010111 00010*", dest: 0 },
    { prefix: "11001000 00010111 00011000 *", dest: 1 },
    { prefix: "11001000 00010111 00011*", dest: 2 },
    { prefix: "11001000 00010111 00011000 *", dest: 3 },

    { prefix: "11001000 00010111 00011100 0000*", dest: 4 },
    { prefix: "11001000 00010111 00011100 0010*", dest: 5 },
    { prefix: "11001000 00010111 00011100 00*", dest: 3 },
    { prefix: "11001000 00010111 00011100 10*", dest: 6 },

    { prefix: "11001000 00010111 110*", dest: 7 },
    { prefix: "11001000 00010111 111*", dest: 7 },
    { prefix: "11001000 00010111 101*", dest: 8 },
    { prefix: "11001000 00010111 1*", dest: 8 },

    { prefix: "11001000 10101010 *", dest: 9 },
    { prefix: "11001000 1010*", dest: 10 },
    { prefix: "11001000 0101*", dest: 10 },
];

const defaultIncomingPackets = [
    { time: 0, addr: "11001000 00010111 00010101 01001100" },
    // tiebreaker.
    { time: 1, addr: "11001000 00010111 00011000 00000000" },
    
    // test some more.
    { time: 2, addr: "11001000 00010111 00011100 00101111" },
    { time: 3, addr: "11001000 00010111 10100110 10001011" },

    // Congestion.
    { time: 4, addr: "11001000 00010111 00011000 00000000" },
    { time: 4, addr: "11001000 00010111 00011000 00000000" },
    { time: 4, addr: "11001000 00010111 00011000 00000000" },
    { time: 4, addr: "11001000 00010111 00011000 00000000" },
    { time: 4, addr: "11001000 00010111 00011000 00000000" },
    { time: 4, addr: "11001000 00010111 00011000 00000000" },
    { time: 4, addr: "11001000 00010111 00011000 00000000" },
];

let incomingPackets = [];

let isRoundRobin = false;
let highPriorityQueue = [];
let lowPriorityQueue = [];
let roundRobinQueues = [];

let forwardingOutput = [];
for (let i = 0; i < 11; i++)
    forwardingOutput.push(null);

for (let i = 0; i < 3; i++)
    roundRobinQueues.push([]);

const routerID = 7983;

function doesAddressMatchPrefix(addr, prefix) {
    const parts = prefix.split(' ');
    for (let iPart = 0; iPart < parts.length; ++iPart) {
        let check = addr[iPart];
        let part = parts[iPart];
        let wildcard = part.indexOf('*');
        if (wildcard == -1) {
            // Test for an exact match.
            if (check !== part)
                return false;
        }
        else {
            // Test the wildcard substring.
            if (!check.startsWith(part.substring(0, wildcard)))
                return false;
        }
    }

    // No errors.
    return true;
}

function getForwardingAddress(inAddr) {
    let matches = [];
    let longest = 0;
    for (let i = 0; i < fwdTable.length; ++i) {
        if (doesAddressMatchPrefix(inAddr, fwdTable[i].prefix)) {
            matches.push(fwdTable[i]);
            if (fwdTable[i].prefix.length > longest)
                longest = fwdTable[i].prefix.length;
        }
    }

    let candidates = [];
    for (let iMatch = 0; iMatch < matches.length; ++iMatch) {
        const match = matches[iMatch];
        if (match.prefix.length == longest)
            candidates.push(match);
    }

    if (candidates.length == 0)
        return null;

    // choose based on the router ID.
    let chosen = routerID % candidates.length;
    console.log(`${candidates.length} candidate(s) (length = ${longest}, choosing index=${chosen})`);
    // for (let i = 0; i < candidates.length; i++)
    //     console.log(JSON.stringify(candidates[i]));

    return candidates[chosen].dest;
}


let packetIndex = 0;
function receiveIncomingPacket() {
    // Receive an incoming packet and "classify" it
    if (incomingPackets.length == 0)
        return;

    let packet = incomingPackets.shift().addr;
    packetIndex++;
    
    console.log(`incoming packet from: ${JSON.stringify(packet)}`)

    if (!isRoundRobin) {
        let isHighPriority = (packetIndex % 3) == 0;
        if (isHighPriority) {
            console.log("\tPlaced in high priority queue.");
            highPriorityQueue.push(packet);
        }
        else {
            console.log("\tPlaced in low priority queue.");
            lowPriorityQueue.push(packet);
        }    
    }
    else {
        // Pick a random queue.
        // let queueIndex = Math.floor(Math.random() * 3);
        let queueIndex = packetIndex % 3;
        console.log(`\tPlaced in RR queue ${queueIndex}`);
        roundRobinQueues[queueIndex].push(packet);
    }
}

function tryToSwitchPacket(packet) {
    let addr = getForwardingAddress(packet.split(' '));
    if (forwardingOutput[addr] != null) {
        console.log(`\tHoL blocking at link interface ${addr}!`);
        return false;
    }

    console.log(`\tPacket sent to link interface: ${addr}`);
    forwardingOutput[addr] = packet;
    return true;
}

function hasInputPacketsQueued() {
    if (highPriorityQueue.length != 0)
        return true;
    if (lowPriorityQueue.length != 0)
        return true;

    for (let iQueue = 0; iQueue < roundRobinQueues.length; ++iQueue) {
        if (roundRobinQueues[iQueue].length != 0)
            return true;
    }

    return false;
}

let RRQueueIndex = 0;
function switchingFabric() {
    if (!isRoundRobin) {
        if (highPriorityQueue.length) {
            let packet = highPriorityQueue[0];
            console.log(`Forwarding packet ${JSON.stringify(packet)} from high priority queue.`);
            if (tryToSwitchPacket(packet))
                highPriorityQueue.shift();

            return true;
        }
        else if (lowPriorityQueue.length) {
            let packet = lowPriorityQueue[0];
            console.log(`Forwarding packet ${JSON.stringify(packet)} from low priority queue.`);
            if (tryToSwitchPacket(packet))
                lowPriorityQueue.shift();

            return true;
        }
    }
    else {
        let iQueue = RRQueueIndex++;
        if (RRQueueIndex >= roundRobinQueues.length) RRQueueIndex = 0;

        if (roundRobinQueues[iQueue].length != 0) {
            let packet = roundRobinQueues[iQueue][0];
            console.log(`Forwarding packet ${JSON.stringify(packet)} from RR queue ${iQueue}.`);
            if (tryToSwitchPacket(packet))
                roundRobinQueues[iQueue].shift();

            return true;
        }
    }

    return false;
}

function runSimulation() {
    let tick = 0;

    while (incomingPackets.length !== 0 || hasInputPacketsQueued()) {
        // Receive all incoming packets.
        while (incomingPackets.length != 0 && incomingPackets[0].time <= tick) {
            receiveIncomingPacket();
        }
    
        // Switch a maximum of two packets at once.
        for (let i = 0; i < 2; i++)
            switchingFabric();
    
        // Simulate packets leaving.
        for (let i = 0; i < forwardingOutput.length; i++)
            forwardingOutput[i] = null;
    
        tick++;
    }
}

console.log(`Running priority queue simulation at: ${new Date().toLocaleString()}`);
incomingPackets = [...defaultIncomingPackets]
runSimulation()


// Reset for round-robin
console.log(`\n\n\nRunning round-robin simulation at: ${new Date().toLocaleString()}`);
isRoundRobin = true
incomingPackets = [...defaultIncomingPackets]
runSimulation()

