# SDN Campus Network

A three-tier campus network emulated in Mininet, segmented with 802.1Q VLANs and protected by a Ryu OpenFlow controller that blocks traffic between departments that shouldn't talk.

**Write-up:** [Segmenting a campus network with SDN](https://cyconic.com/projects/sdn-campus-network/) explains the design, how it was verified, and its limitations.

## What it builds

```
                 r0   router, one link per VLAN
                 │
                 s1   core   ← ACLs live here
            ┌────┴────┐
            s2        s3     distribution
          ┌─┴─┐     ┌─┴─┐
          s4  s5    s6  s7   access
          │   │     │   │
          h1  h2    h3  h4
          ECE CS    Admin Labs
```

| VLAN | Department     | Subnet          | Addressing                                  |
|------|----------------|-----------------|---------------------------------------------|
| 10   | ECE            | 192.168.10.0/24 | DHCP `.100–.200`; router also serves DNS    |
| 20   | CS             | 192.168.20.0/24 | DHCP `.100–.200`                            |
| 30   | Administration | 192.168.30.0/24 | Static server at `192.168.30.10`            |
| 40   | Student labs   | 192.168.40.0/24 | DHCP `.100–.200`                            |

- **VLANs:** Open vSwitch access ports for hosts, trunks carrying all four VLANs between switches.
- **Inter-VLAN routing:** a Linux router (`r0`) with four links into the core switch, one access port per VLAN, each holding that VLAN's `.1` gateway.
- **DHCP and DNS:** one `dnsmasq` instance per VLAN interface on `r0`, plus an internal `cust.local` zone (for example `admin.cust.local`). The script flags any host that leases an address from the wrong VLAN's pool.
- **Routing:** FRRouting (`zebra` + `ospfd`) on `r0`, all subnets in OSPF area 0.
- **Controller (`src/customRyu.py`):** installs a priority-0 rule that hands traffic to OVS's normal switching (`OFPP_NORMAL`), then priority-40000 drop rules on the core switch:
  - Student labs (VLAN 40) → Administration (VLAN 30): **drop**
  - ECE (VLAN 10) → CS (VLAN 20): **drop**
- **Fail closed:** switches run in `fail-mode secure`, so they forward nothing if the controller is down.

## Requirements

Tested on Ubuntu with:

- [Mininet](http://mininet.org/) and Open vSwitch
- [Ryu](https://ryu-sdn.org/) (run here from the `osrg/ryu` Docker image)
- FRRouting (`/usr/lib/frr/zebra`, `/usr/lib/frr/ospfd`)
- `dnsmasq`, `isc-dhcp-client` (`dhclient`), `ethtool`
- Python 3

## Running it

1. Start the controller (from the repo root):

   ```bash
   sudo docker run --rm --network host -v "$PWD/src:/apps" osrg/ryu \
     ryu-manager /apps/customRyu.py
   ```

2. In another terminal, build the network:

   ```bash
   sudo python3 src/campusNetwork.py
   ```

   It brings up the topology, tags the VLANs, starts FRR and DHCP/DNS, leases addresses to `h1`, `h2` and `h4`, then drops you into the Mininet CLI.

## Verifying the policy

```text
mininet> h4 ping -c 3 192.168.30.10          # labs → admin: 100% packet loss
mininet> sh ovs-ofctl -O OpenFlow13 dump-flows s1
```

The labs → admin drop rule's `n_packets` counter goes up by exactly the number of blocked pings, which confirms the ACL, not something else, dropped them. Allowed paths work normally:

```text
mininet> h3 python3 -m http.server 80 &
mininet> h1 curl http://192.168.30.10        # ECE → admin: allowed
mininet> h2 nslookup admin.cust.local        # internal DNS
```

## Repository contents

| Path | What it is |
|------|------------|
| `src/campusNetwork.py` | Mininet topology, VLAN tagging, FRR, DHCP/DNS, lease checks |
| `src/customRyu.py` | Ryu controller app: NORMAL pipeline + ACL drop rules |
| `captures/dhcpDora.pcapng` | DHCP Discover/Offer/Request/ACK in VLAN 10 |
| `captures/campus_traffic.pcap` | Traffic from an earlier, unsegmented version (note the ICMP redirects) |
| `captures/student_traffic.pcap` | Background traffic capture |
| `docs/CCN Project Report.pdf` | Full project report with screenshots and protocol analysis |

## Known limitations

- ACLs match on source IP, which hosts control. Matching on VLAN tag or ingress port would be stronger.
- Rules are stateless, so they block replies too: admin can't use services in the labs either.
- IPv4 only (`eth_type=0x0800`).
- OSPF runs on a single router, so it has no neighbours to exchange routes with.
- Policy is hard-coded in `customRyu.py`.

See the [write-up](https://cyconic.com/projects/sdn-campus-network/) for details.

## License

[MIT](LICENSE)
