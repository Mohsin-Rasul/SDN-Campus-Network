"""
CUST Smart Campus Network - Three-Tier VLAN Topology with 802.1Q Tagging + SDN
Integrated with OSPF (FRRouting) bypass for Mininet namespaces.
"""

import time
import os
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import Node, RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel


class OSPFRouter(Node):
    def config(self, **params):
        super(OSPFRouter, self).config(**params)
        self.cmd('sysctl net.ipv4.ip_forward=1')

    def start_ospf(self):
        # 1. Fix the Linux folder permission crashes
        self.cmd('mkdir -p /var/run/frr')
        self.cmd('chown -R root:root /var/run/frr 2>/dev/null')
        self.cmd('chmod 777 /var/run/frr')

        # 2. Create isolated config files
        zebra_conf = "/tmp/zebra_r0.conf"
        ospfd_conf = "/tmp/ospfd_r0.conf"

        with open(zebra_conf, 'w') as f:
            f.write("hostname r0\npassword zebra\n")

        with open(ospfd_conf, 'w') as f:
            f.write("hostname r0\npassword zebra\n")
            f.write("router ospf\n")
            f.write(" ospf router-id 192.168.10.1\n")
            f.write(" network 192.168.10.0/24 area 0\n")
            f.write(" network 192.168.20.0/24 area 0\n")
            f.write(" network 192.168.30.0/24 area 0\n")
            f.write(" network 192.168.40.0/24 area 0\n")

        # 3. Kill existing dead instances
        self.cmd('pkill -9 -f ospfd 2>/dev/null')
        self.cmd('pkill -9 -f zebra 2>/dev/null')

        # 4. Launch Daemons AS ROOT using the standard system socket
        print("    - Starting Zebra core routing engine...")
        self.cmd('/usr/lib/frr/zebra -f {} -i /var/run/frr/zebra.pid -z /var/run/frr/zserv.api -d -A 127.0.0.1 -u root -g root'.format(zebra_conf))
        time.sleep(1)
        
        print("    - Starting OSPF routing engine...")
        self.cmd('/usr/lib/frr/ospfd -f {} -i /var/run/frr/ospfd.pid -z /var/run/frr/zserv.api -d -A 127.0.0.1 -u root -g root'.format(ospfd_conf))

    def terminate(self):
        self.cmd('pkill -9 -f ospfd')
        self.cmd('pkill -9 -f zebra')
        self.cmd('sysctl net.ipv4.ip_forward=0')
        super(OSPFRouter, self).terminate()


class CustCampusTopo(Topo):
    def build(self):
        r0 = self.addNode('r0', cls=OSPFRouter)
        s1_core = self.addSwitch('s1')

        s2_dist_east = self.addSwitch('s2')
        s3_dist_west = self.addSwitch('s3')

        s4_access_ece = self.addSwitch('s4')
        s5_access_cs = self.addSwitch('s5')
        s6_access_admin = self.addSwitch('s6')
        s7_access_labs = self.addSwitch('s7')

        h1_ece_pc = self.addHost('h1', ip=None)
        h2_cs_pc = self.addHost('h2', ip=None)
        h3_admin_pc = self.addHost('h3', ip=None)
        h4_lab_pc = self.addHost('h4', ip=None)

        self.addLink(r0, s1_core, intfName1='r0-eth1', params1={'ip': '192.168.10.1/24'})
        self.addLink(r0, s1_core, intfName1='r0-eth2', params1={'ip': '192.168.20.1/24'})
        self.addLink(r0, s1_core, intfName1='r0-eth3', params1={'ip': '192.168.30.1/24'})
        self.addLink(r0, s1_core, intfName1='r0-eth4', params1={'ip': '192.168.40.1/24'})

        self.addLink(s1_core, s2_dist_east)
        self.addLink(s1_core, s3_dist_west)

        self.addLink(s2_dist_east, s4_access_ece)
        self.addLink(s2_dist_east, s5_access_cs)
        self.addLink(s3_dist_west, s6_access_admin)
        self.addLink(s3_dist_west, s7_access_labs)

        self.addLink(h1_ece_pc, s4_access_ece)
        self.addLink(h2_cs_pc, s5_access_cs)
        self.addLink(h3_admin_pc, s6_access_admin)
        self.addLink(h4_lab_pc, s7_access_labs)


def real_port_name(net, switch_name, peer_node_name, peer_intf_hint=None):
    switch = net[switch_name]
    for intf in switch.intfList():
        if intf.name == 'lo':
            continue
        link = intf.link
        if link is None:
            continue
        other_intf = link.intf1 if link.intf2 == intf else link.intf2
        if other_intf is None or other_intf.node is None:
            continue
        if other_intf.node.name == peer_node_name:
            if peer_intf_hint is None or peer_intf_hint == other_intf.name:
                return intf.name
    return None


def tag_access_port(net, switch_name, intf_name, vlan_id, label=''):
    if intf_name is None:
        return False
    net[switch_name].cmd('ovs-vsctl set port {} tag={}'.format(intf_name, vlan_id))
    print("    - {:>3} : {:<10} -> ACCESS vlan{:<4} ({})".format(switch_name, intf_name, vlan_id, label))
    return True


def tag_trunk_port(net, switch_name, intf_name, vlan_ids, label=''):
    if intf_name is None:
        return False
    vlans = ','.join(str(v) for v in vlan_ids)
    net[switch_name].cmd('ovs-vsctl set port {} trunks={}'.format(intf_name, vlans))
    print("    - {:>3} : {:<10} -> TRUNK ({}) ({})".format(switch_name, intf_name, vlans, label))
    return True


def setup_vlans(network):
    print("\n*** Applying 802.1Q VLAN tagging and enforcing OpenFlow 1.3...")

    for sw in network.switches:
        sw.cmd('ovs-vsctl set bridge {} protocols=OpenFlow13'.format(sw.name))
        sw.cmd('ovs-vsctl set-fail-mode {} secure'.format(sw.name))

    VLAN_ECE, VLAN_CS, VLAN_ADMIN, VLAN_LABS = 10, 20, 30, 40
    ALL_VLANS = [VLAN_ECE, VLAN_CS, VLAN_ADMIN, VLAN_LABS]

    tag_access_port(network, 's1', real_port_name(network, 's1', 'r0', 'r0-eth1'), VLAN_ECE, 'r0-eth1 / ECE')
    tag_access_port(network, 's1', real_port_name(network, 's1', 'r0', 'r0-eth2'), VLAN_CS, 'r0-eth2 / CS')
    tag_access_port(network, 's1', real_port_name(network, 's1', 'r0', 'r0-eth3'), VLAN_ADMIN, 'r0-eth3 / Admin')
    tag_access_port(network, 's1', real_port_name(network, 's1', 'r0', 'r0-eth4'), VLAN_LABS, 'r0-eth4 / Labs')

    tag_trunk_port(network, 's1', real_port_name(network, 's1', 's2'), ALL_VLANS, 's1->s2')
    tag_trunk_port(network, 's1', real_port_name(network, 's1', 's3'), ALL_VLANS, 's1->s3')

    tag_trunk_port(network, 's2', real_port_name(network, 's2', 's1'), ALL_VLANS, 's2->s1')
    tag_trunk_port(network, 's2', real_port_name(network, 's2', 's4'), ALL_VLANS, 's2->s4')
    tag_trunk_port(network, 's2', real_port_name(network, 's2', 's5'), ALL_VLANS, 's2->s5')

    tag_trunk_port(network, 's3', real_port_name(network, 's3', 's1'), ALL_VLANS, 's3->s1')
    tag_trunk_port(network, 's3', real_port_name(network, 's3', 's6'), ALL_VLANS, 's3->s6')
    tag_trunk_port(network, 's3', real_port_name(network, 's3', 's7'), ALL_VLANS, 's3->s7')

    tag_trunk_port(network, 's4', real_port_name(network, 's4', 's2'), ALL_VLANS, 's4->s2')
    tag_access_port(network, 's4', real_port_name(network, 's4', 'h1'), VLAN_ECE, 's4->h1')

    tag_trunk_port(network, 's5', real_port_name(network, 's5', 's2'), ALL_VLANS, 's5->s2')
    tag_access_port(network, 's5', real_port_name(network, 's5', 'h2'), VLAN_CS, 's5->h2')

    tag_trunk_port(network, 's6', real_port_name(network, 's6', 's3'), ALL_VLANS, 's6->s3')
    tag_access_port(network, 's6', real_port_name(network, 's6', 'h3'), VLAN_ADMIN, 's6->h3')

    tag_trunk_port(network, 's7', real_port_name(network, 's7', 's3'), ALL_VLANS, 's7->s3')
    tag_access_port(network, 's7', real_port_name(network, 's7', 'h4'), VLAN_LABS, 's7->h4')


def start_dhcp_services(network):
    """
    THREE SEPARATE dnsmasq instances, one per VLAN interface.

    DNS UPDATE: the 'ece' instance now also serves internal DNS (port=53
    instead of port=0), since DNS lookups aren't subnet-bound the way
    DHCP broadcasts are - any host that can route to r0-eth1's IP can
    query it for names, regardless of which VLAN that host is on. This
    gives the campus internal name resolution (e.g. admin.cust.local)
    without needing NAT/internet access, which is intentionally out of
    scope for this simulation. All three pools' dhcp-option=6 (DNS
    server) now point at 192.168.10.1, where DNS is actually listening,
    instead of the old 192.168.30.10 (Admin host, which never ran DNS).
    """
    r0 = network['r0']
    r0.cmd('pkill dnsmasq 2>/dev/null')
    time.sleep(0.5)

    configs = {
        'ece': {
            'iface': 'r0-eth1', 'conf': '/tmp/dnsmasq_ece.conf', 'pid': '/tmp/dnsmasq_ece.pid',
            'body': ("port=53\ninterface=r0-eth1\nbind-interfaces\nexcept-interface=lo\ndhcp-authoritative\n"
                     "dhcp-range=192.168.10.100,192.168.10.200,255.255.255.0,12h\n"
                     "dhcp-option=3,192.168.10.1\ndhcp-option=6,192.168.10.1\n"
                     "no-resolv\n"
                     "domain=cust.local\n"
                     "expand-hosts\n"
                     "address=/admin.cust.local/192.168.30.10\n"
                     "address=/ece.cust.local/192.168.10.1\n"
                     "address=/cs.cust.local/192.168.20.1\n"
                     "address=/labs.cust.local/192.168.40.1\n"
                     "address=/portal.cust.local/192.168.30.10\n"),
        },
        'cs': {
            'iface': 'r0-eth2', 'conf': '/tmp/dnsmasq_cs.conf', 'pid': '/tmp/dnsmasq_cs.pid',
            'body': ("port=0\ninterface=r0-eth2\nbind-interfaces\nexcept-interface=lo\ndhcp-authoritative\n"
                     "dhcp-range=192.168.20.100,192.168.20.200,255.255.255.0,12h\n"
                     "dhcp-option=3,192.168.20.1\ndhcp-option=6,192.168.10.1\n"),
        },
        'labs': {
            'iface': 'r0-eth4', 'conf': '/tmp/dnsmasq_labs.conf', 'pid': '/tmp/dnsmasq_labs.pid',
            'body': ("port=0\ninterface=r0-eth4\nbind-interfaces\nexcept-interface=lo\ndhcp-authoritative\n"
                     "dhcp-range=192.168.40.100,192.168.40.200,255.255.255.0,12h\n"
                     "dhcp-option=3,192.168.40.1\ndhcp-option=6,192.168.10.1\n"),
        },
    }

    for name, cfg in configs.items():
        with open(cfg['conf'], 'w') as f:
            f.write(cfg['body'])
        r0.cmd('dnsmasq -C {conf} --pid-file={pid} 2>&1'.format(**cfg))
        time.sleep(0.5)
        pid_check = r0.cmd('cat {} 2>/dev/null'.format(cfg['pid'])).strip()
        if pid_check and pid_check.isdigit():
            print("    - dnsmasq for {} VLAN bound to {} (pid {})".format(name, cfg['iface'], pid_check))
            
    time.sleep(2)


def request_dhcp_lease(network, host_name, iface, expected_subnet, gateway):
    host = network[host_name]
    
    for attempt in range(2): 
        host.cmd('pkill -9 -f "dhclient.*{}" 2>/dev/null'.format(iface))
        host.cmd('ip addr flush dev {} 2>/dev/null'.format(iface))
        time.sleep(1)

        cmd = 'timeout 15 dhclient -lf /tmp/{0}.leases -pf /tmp/{0}.pid -v {1} > /tmp/{0}_dhclient.log 2>&1'.format(host_name, iface)
        host.cmd(cmd)
        time.sleep(1.5)

        ip_output = host.cmd('ip -4 addr show {}'.format(iface))
        if 'inet ' in ip_output:
            ip_line = [l.strip() for l in ip_output.splitlines() if 'inet ' in l][0]
            leased_ip = ip_line.split()[1].split('/')[0]
            
            if expected_subnet in leased_ip:
                print("    - {} leased: {} (correct VLAN pool)".format(host_name, ip_line))
                return True
            else:
                print("    !! VLAN LEAK: {} leased {} but expected {}.x".format(host_name, leased_ip, expected_subnet))
                return False
                
        if attempt == 0:
            print("    - {} DHCP attempt 1 timed out. Retrying with clean state...".format(host_name))

    print("    !! WARNING: {} did NOT receive a DHCP lease. Check /tmp/{}_dhclient.log".format(host_name, host_name))
    return False


def execute_network():
    topology = CustCampusTopo()
    network = Mininet(topo=topology, controller=RemoteController)
    network.start()

    print("\n*** [1/5] Core router interfaces are up")
    
    r0 = network['r0']
    r0.cmd('ifconfig r0-eth1 192.168.10.1 netmask 255.255.255.0 up')
    r0.cmd('ifconfig r0-eth2 192.168.20.1 netmask 255.255.255.0 up')
    r0.cmd('ifconfig r0-eth3 192.168.30.1 netmask 255.255.255.0 up')
    r0.cmd('ifconfig r0-eth4 192.168.40.1 netmask 255.255.255.0 up')
    
    print("*** [1.5/5] Launching isolated OSPF Daemons inside r0...")
    r0.start_ospf()

    for node in network.values():
        for intf in node.intfList():
            if intf.name != 'lo':
                node.cmd('ethtool --offload {} tx off rx off 2>/dev/null'.format(intf.name))

    setup_vlans(network)

    print("\n*** Waiting 5 seconds for Ryu Controller to synchronize with all switches...")
    time.sleep(5)

    print("\n*** [2/5] Starting centralized DHCP service on r0 (per-VLAN)...")
    start_dhcp_services(network)

    print("*** [3/5] Assigning static service IP to Admin host (h3)...")
    network['h3'].setIP('192.168.30.10', 24)
    network['h3'].cmd('route add default gw 192.168.30.1')

    print("*** [4/5] Requesting DHCP leases for h1 (ECE), h2 (CS), h4 (Labs)...")
    request_dhcp_lease(network, 'h1', 'h1-eth0', '192.168.10.', '192.168.10.1')
    request_dhcp_lease(network, 'h2', 'h2-eth0', '192.168.20.', '192.168.20.1')
    request_dhcp_lease(network, 'h4', 'h4-eth0', '192.168.40.', '192.168.40.1')

    print("\n*** Network is up with true isolated OSPF Routing and internal DNS (cust.local).")
    print("    Try: h2 nslookup admin.cust.local")
    print("         h4 nslookup labs.cust.local")
    CLI(network)

    network['r0'].cmd('pkill dnsmasq 2>/dev/null')
    network.stop()


if __name__ == '__main__':
    setLogLevel('info')
    os.system("rm -f /tmp/*dhcp* 2>/dev/null")
    execute_network()
