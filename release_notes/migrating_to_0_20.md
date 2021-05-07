# NGS CLI v 0.20.0

Version 0.20 brings compatibility with JWT v2 functionality added to the NATS ecosystem. Future updates to NGS will introduce features like JetStream which will require version 2 if not deployed as a leaf node.

NGS is fully compatible with JWT v1 or v2 projects. However, the tooling that is used to manage your account (`ngs` cli) and your configurations (`nsc`) determines the version `ngs` cli that you can use, so you should update now, simply to have it at the current version.

However, by default the `ngs` cli installer will default to `nsc` at its latest version. If you are starting a new project, stop reading as the tooling will be fully compatible.

If you are using `nsc` 0.5.0, you'll want to ensure that the installer didn't install a newer version of `nsc`. You can easily downgrade by executing the command: `nsc update --version 0.5.0`.

If you are using `nsc` 2.x but tried `ngs` in the past, you'll want to ensure you update your `ngs` tool to its current version.

Finally, note that if you have on-prem servers, only `nats-server` 2.2.0 or better support v2. If you are running older servers, don't upgrade your configurations, and stay on nsc 0.5.0.



The following matrix describes compatibility between `nsc`, `ngs cli`:

|              | JWT v1               | JWT v2             |
|---           |:---:                 |---                 |
| nsc 0.5.0    |  :heavy_check_mark:  | :x:                |
| nsc 2.2.3    |  :x:                 | :heavy_check_mark: |
| ngs cli 0.12 |  :heavy_check_mark:  | :x:                |
| ngs cli 0.20 |  :heavy_check_mark:  | :heavy_check_mark: |


If you see an error like `Error: error reading root: unexpected "ed25519-nkey" algorithm` coming from `nsc` or `ngs` cli, you have a mismatch. The JWTs you are trying to read are version 2. 



# Upgrading your project to use v2 and nsc 2.x

First back up your store and keys, run `nsc env` and note where the `Stores Dir` and `$NKEYS_PATH` are looking for data. 

Next make sure you are using the latest version of `nsc` by executing: `nsc update`

The process of upgrading your JWT account configuration depends on the version of the operator. If you want to update your configurations, simply update the operator: `nsc add operator --force -u synadia` Changes to your JWT account configurations won't happen until you update the configuration.

That is it! If you have any question please contact us at support@synadia.com.


