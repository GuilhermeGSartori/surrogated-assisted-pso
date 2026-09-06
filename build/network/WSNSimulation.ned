import inet.networklayer.configurator.ipv4.Ipv4NetworkConfigurator;
import inet.node.inet.StandardHost;
import inet.physicallayer.wireless.ieee802154.packetlevel.Ieee802154NarrowbandScalarRadioMedium;

network WSNSimulation
{
    parameters:
        int numNodes;
        int numRelays;

        @display("bgb=1000,700");

    submodules:

        // ========================================================
        // IPv4 address and routing configuration
        // ========================================================

        configurator: Ipv4NetworkConfigurator {
            @display("p=100,50");
        }


        // ========================================================
        // Wireless medium
        // ========================================================

        radioMedium: Ieee802154NarrowbandScalarRadioMedium {
            @display("p=300,50");
        }


        // ========================================================
        // Sensor nodes
        // ========================================================

        node[numNodes]: StandardHost {
            parameters:
                numWlanInterfaces = 1;

                @display("p=200,300");
        }


        // ========================================================
        // Relay nodes
        // ========================================================

        relay[numRelays]: StandardHost {
            parameters:
                numWlanInterfaces = 1;

                @display("p=500,300");
        }


        // ========================================================
        // Sink
        // ========================================================

        sink: StandardHost {
            parameters:
                numWlanInterfaces = 1;

                @display("p=800,300");
        }
}