import inet.networklayer.configurator.ipv4.Ipv4NetworkConfigurator;
import inet.node.inet.StandardHost;
import inet.physicallayer.wireless.ieee802154.packetlevel.Ieee802154NarrowbandScalarRadioMedium;

network RangeCalibration
{
    parameters:
        @display("bgb=600,300");

    submodules:
        configurator: Ipv4NetworkConfigurator {
            @display("p=100,50");
        }

        radioMedium: Ieee802154NarrowbandScalarRadioMedium {
            @display("p=300,50");
        }

        tx: StandardHost {
            parameters:
                numWlanInterfaces = 1;
                @display("p=150,200");
        }

        rx: StandardHost {
            parameters:
                numWlanInterfaces = 1;
                @display("p=450,200");
        }
}