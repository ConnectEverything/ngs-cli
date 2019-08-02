# NGS

The `ngs` command line tool is used to manage your billing account on Synadia's global messaging service built with NATS. Access to the service relies on the use of Account and User JWTs. These JWTs can be configured and set up locally using the open source tool [nsc](https://github.com/nats-io/nsc). Installing `ngs` using the instructions below will also install `nsc`.

See [the Synadia site](https://synadia.com/ngs/signup) for more information on how to sign up for Synadia's service. The [NATS documentation site](https://nats-io.github.io/docs/nats_tools/nsc/) has information about using `nsc` to setup a new account and deploy it.

## Install

With Python:

```python
curl https://downloads.synadia.com/ngs/install.py -sSf | python
```

Direct Download:

Download your platform binary from [here.](https://github.com/connecteverything/ngs-cli/releases/latest)

## Updates are easy

`ngs update` will download and install the latest version.