from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3

class CustomCampusController(app_manager.RyuApp):
    # Strictly enforce OpenFlow 1.3
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(CustomCampusController, self).__init__(*args, **kwargs)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # 1. THE HYBRID SDN FIX: 
        # Push a default table-miss flow to all connecting switches.
        # This tells the switch to use its native OVS pipeline (respecting VLAN tags)
        # for any traffic that doesn't match our specific security drops.
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        self.add_flow(datapath, 0, match, actions)
        
        self.logger.info("Switch fully connected and NORMAL flow pushed: %s", datapath.id)
        
        # 2. Apply Custom Security Policies ONLY to the Core Switch (s1)
        if datapath.id == 1: 
            self.logger.info("Applying CUST campus ACL policy to Core Switch (s1)...")
            self.apply_custom_firewall(datapath)

    def add_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                match=match, instructions=inst)
        datapath.send_msg(mod)

    def apply_custom_firewall(self, datapath):
        parser = datapath.ofproto_parser
        
        # Rule 1: Student Labs (40) to Admin (30) Drop
        match1 = parser.OFPMatch(
            eth_type=0x0800,
            ipv4_src='192.168.40.0/255.255.255.0',
            ipv4_dst='192.168.30.0/255.255.255.0')
        self.add_flow(datapath, 40000, match1, [])
        self.logger.info("ACL Rule 1 installed: Student_Labs(40) -> Admin(30) DROP")

        # Rule 2: ECE (10) to CS (20) Drop
        match2 = parser.OFPMatch(
            eth_type=0x0800,
            ipv4_src='192.168.10.0/255.255.255.0',
            ipv4_dst='192.168.20.0/255.255.255.0')
        self.add_flow(datapath, 40000, match2, [])
        self.logger.info("ACL Rule 2 installed: ECE_Dept(10) -> CS_Dept(20) DROP")
