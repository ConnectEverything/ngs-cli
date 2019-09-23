# NGS

The `ngs` command line tool is used to manage your billing account on Synadia's global messaging service built with NATS. Access to the service relies on the use of Account and User JWTs. These JWTs can be configured and set up locally using the open source tool [nsc](https://github.com/nats-io/nsc). Installing `ngs` using the instructions below will also install the open source `nsc` tool.

See [the Synadia site](https://synadia.com/ngs/signup) for more information on how to sign up for Synadia's service and the [NATS documentation site](https://nats-io.github.io/docs/nats_tools/nsc/) for information about using `nsc` to manage your NATS account.

## Install

With Python:

```python
curl https://downloads.synadia.com/ngs/install.py -sSf | python
```

Direct Download:

Download your platform binary from [here.](https://github.com/connecteverything/ngs-cli/releases/latest)

## Updates are easy

`ngs update` will download and install the latest version.

## Release Notes

With 0.9 we are simplifying the NGS tool and relying heavily on the open source `nsc` tool for all JWT editing and creation. More information about migrating to this new version can be found [here](release_notes/migrating_to_0_9.md).
