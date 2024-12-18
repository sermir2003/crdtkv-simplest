# CRDT KV Simplest

Simple operation-based Conflict-free Replicated Data Type as a key-to-value mapping with policy Last-Write-Wins.

## Installation and launch

```bash
git clone git@github.com:sermir2003/crdtkv-simplest.git  # Склонируйте
cd crdtkv-simplest
python3 -m venv .venv  # Установите зависимости, например так
source .venv/bin/activate
pip install -r requirements.txt
docker build -t node_image .  # Соберите образ
docker network create --driver bridge crdt_network  # Создайте отдельную сеть для симуляции проблем
./run_node.py node-*
```

## Sending requests

```bash
# Чтобы оказаться в одной с контейнерами сети
docker run -it --name observer --network crdt_network --entrypoint /bin/sh alpine:latest
# В контейнере чтобы установить curl
apk update && apk add curl
```

Or

```bash
docker exec -it node-* curl ...
```

### Examples of service requests

#### Patch

```bash
curl -X PATCH http://node-*:5000/items -H "Content-Type: application/json" -d '{"key1": "value1", "key2": "value2"}'
```

#### Get the whole table

```bash
curl -X GET http://node-*:5000/items
```

#### Get value by key

```bash
curl -X GET http://node-*:5000/items/key1
```

## Simulation of network problems

```bash
docker network ls | grep crdt_network
export crdt_network_id=...
ip link | grep "veth.*br-$crdt_network_id"
```

```bash
# loss in 33% cases
sudo tc qdisc add dev $item root netem loss 33%
# duplicate in 50% cases
sudo tc qdisc add dev $item root netem duplicate 50%
# add 30ms as base delay and random jitter (variation in latency) of up to 25ms
sudo tc qdisc add dev $item root netem delay 30ms 25ms
# reorder 25% packages by adding to their delay 10ms, consecutive packets are reordered in 50% cases
sudo tc qdisc add dev $item root netem delay 10ms reorder 25% 50%
# or any combination
sudo tc qdisc add dev $item root netem delay 30ms 25ms loss 33% duplicate 5% reorder 25% 50%
# This applies:
#   30ms base latency with 25ms jitter
#    33% packet loss
#    5% packet duplication
#    25% packet reordering with a 50% correlation

sudo tc qdisc del dev $item root
```
