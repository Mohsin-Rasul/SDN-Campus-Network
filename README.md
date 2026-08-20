
# SDN Campus Network Framework 

## Overview

This project implements a Software Defined Networking (SDN) framework designed specifically to streamline the management of complex campus networks. In traditional settings, the rapid influx of heterogeneous devices and the widespread adoption of Bring Your Own Device (BYOD) policies make manual network configuration by IT administrators tedious, inefficient, and highly complex.

This framework solves that friction by migrating to an SDN paradigm, providing a programmable network platform that incorporates centralized, network-wide rules rather than relying on manual switch-by-switch configuration.

## Core Features

* **Multi-Controller Architecture:** Employs multiple programmable controllers to reliably handle the heterogeneous nature and high traffic loads of modern, multi-layered campus environments.


* **Automated BYOD Policy Enforcement:** Allocates different network functions across various infrastructures automatically based on predefined IT policies, abstracting away the difficulty of individual device management.


* **Centralized Network Visibility:** Leverages the core concepts of SDN to provide global network visibility and central administration over a dispersed, heterogeneous network infrastructure.


* **Enhanced Performance & Security:** Designed to yield flexible campus network management, highly efficient data transmission, and robust network security while guaranteeing long-term network evolution.



## The Problem it Solves

In standard campus architectures, critical management decisions are distributed across interconnected hardware, requiring network administrators to individually configure switches and routers. Owing to the complexity of campus network policies, using traditional approaches to implement network-wide rules is incredibly difficult and highly prone to management error.

By migrating the control plane to this centralized SDN framework, administrators can seamlessly manage users, dynamically route services, and secure the network without touching a single physical device interface.

## Quick Start Guide

### Prerequisites

* An OpenFlow-compatible SDN Controller environment (e.g., Ryu, POX, or Floodlight).
* Mininet (for testing and campus topology emulation).
* Python 3.x

### Installation & Deployment

1. Clone the repository to your local machine:
`git clone [https://github.com/Mohsin-Rasul/ccn-project.git](https://github.com/Mohsin-Rasul/ccn-project.git)`
2. Initialize the multi-controller framework and bind it to your OpenFlow infrastructure.
3. Define your campus BYOD routing and security policies within the centralized configuration directory.
4. Start the network emulator (or connect to physical switches) to see the framework automatically authenticate, manage, and route heterogeneous device traffic based on your predefined rules.

---
