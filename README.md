# bsc gasprice by xinqiyang

estimates binance smartchain gas price based on recent blocks and provides a simple api.


## hosted

- https://coinphd.com/api/gasprice (kindly deployed by [coinphd](https://coinphd.com/))


## installation

requires python 3.6 and an use bsc rpc node allow setting up `filter`.

there is an example of systemd service if you want to run it as a service.

## usage
run develop:
```bash
python gasprice.py
```
start with docker:
```bash
docker-compose up -d --build
```
## api
- metamask format support.
```json
{
  "health": true,
  "block_number": 6725827,
  "SafeGasPrice": 5.0,
  "ProposeGasPrice": 5.0,
  "FastGasPrice": 5.892,
  "InstantGasPrice": 11.0,
  "block_time": 3
}
```

`SafeGasPrice`, `ProposeGasPrice` values represent minimal gas price of the latest 100 blocks. by default slow represents 30% probability, standard is 60%, fast is 90% and instant is 100%.

`FastGasPrice` and `InstantGasPrice` values represent average and max gas price of pre block.
