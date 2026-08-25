import inet.networklayer.configurator.ipv4.Ipv4NetworkConfigurator;
import inet.physicallayer.wireless.ieee802154.packetlevel.Ieee802154NarrowbandScalarRadioMedium;

network WSNSimulation
{
    parameters:
        int numNodes;
        int numRelays;

    submodules:
        configurator: Ipv4NetworkConfigurator {
            @display("p=100,100");
        }

        radioMedium: Ieee802154NarrowbandScalarRadioMedium {
            @display("p=100,200");
        }

        node[numNodes]: SensorNode {
            @display("p=300,200");
        }

        relay[numRelays]: SensorNode {
            @display("p=500,200");
        }

        sink: SensorNode {
            @display("p=700,200");
        }
}